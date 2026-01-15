"""
orac.services.generation_service
---------------------------------
Business logic for text generation with topic support and backend execution.

Handles:
- Topic resolution and validation
- Model selection and configuration
- Grammar file resolution (backend-generated or static)
- Prompt formatting
- Text generation via llama.cpp client
- Backend command execution
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException

from orac.logger import get_logger
from orac.config import load_model_configs, NetworkConfig
from orac.models import GenerationRequest, GenerationResponse
from orac.llama_cpp_client import LlamaCppClient
from orac.topic_manager import TopicManager
from orac.backend_manager import BackendManager
from orac.backend_grammar_generator import BackendGrammarGenerator

logger = get_logger(__name__)


class GenerationService:
    """Service for handling text generation with topic support and backend execution."""

    def __init__(
        self,
        client: LlamaCppClient,
        topic_manager: TopicManager,
        backend_manager: BackendManager,
        backend_grammar_generator: BackendGrammarGenerator,
        last_command_storage: Dict[str, Any]
    ):
        self.client = client
        self.topic_manager = topic_manager
        self.backend_manager = backend_manager
        self.backend_grammar_generator = backend_grammar_generator
        self.last_command_storage = last_command_storage

    async def generate_text(
        self,
        request: GenerationRequest,
        topic_id: str = "general"
    ) -> GenerationResponse:
        """
        Generate text using a topic configuration.

        Args:
            request: Generation request with prompt and settings
            topic_id: Topic identifier (defaults to "general")

        Returns:
            GenerationResponse with generated text and metadata

        Raises:
            HTTPException: On validation or generation errors
        """
        start_time = datetime.now()
        try:
            # Store the last command and set processing status
            self.last_command_storage["command"] = request.prompt
            self.last_command_storage["topic"] = topic_id
            self.last_command_storage["timestamp"] = start_time
            self.last_command_storage["status"] = "processing"
            self.last_command_storage["start_time"] = start_time
            self.last_command_storage["end_time"] = None
            self.last_command_storage["elapsed_ms"] = None
            self.last_command_storage["error"] = None
            self.last_command_storage["success"] = False
            self.last_command_storage["generated_json"] = None

            # Extract timing metadata from upstream services
            timing = self.last_command_storage.get("timing", {})
            if request.metadata:
                timing["wake_word_time"] = request.metadata.get("wake_word_time")
                timing["recording_end_time"] = request.metadata.get("recording_end_time")
                timing["stt_start_time"] = request.metadata.get("stt_start_time")
                timing["stt_end_time"] = request.metadata.get("stt_end_time")
                logger.info(f"Received timing metadata: wake_word={timing.get('wake_word_time')}")
            timing["llm_start_time"] = start_time.isoformat()
            self.last_command_storage["timing"] = timing

            # Get or auto-discover topic
            topic = self.topic_manager.get_topic(topic_id)
            if not topic:
                # Auto-discover new topic
                logger.info(f"Auto-discovering new topic: {topic_id}")
                topic = self.topic_manager.auto_discover_topic(topic_id)

            # Check if topic is enabled
            if not topic.enabled:
                raise HTTPException(
                    status_code=403,
                    detail=f"Topic '{topic_id}' is disabled"
                )

            # Mark topic as used
            self.topic_manager.mark_topic_used(topic_id)

            # Get the model from topic or request
            model_to_use = request.model or topic.model

            if not model_to_use:
                raise HTTPException(
                    status_code=400,
                    detail="No model configured for topic and none specified in request"
                )

            # Load model configs to get default settings for the model
            model_configs = load_model_configs()
            model_config = model_configs.get("models", {}).get(model_to_use, {})

            # Use request settings, then topic settings, then model defaults
            temperature = request.temperature if request.temperature is not None else topic.settings.temperature
            top_p = request.top_p if request.top_p is not None else topic.settings.top_p
            top_k = request.top_k if request.top_k is not None else topic.settings.top_k
            max_tokens = request.max_tokens if request.max_tokens is not None else topic.settings.max_tokens
            json_mode = request.json_mode if request.json_mode is not None else topic.settings.force_json

            # Resolve grammar file
            grammar_file = self._resolve_grammar_file(request, topic, topic_id)

            # Format the prompt
            formatted_prompt = self._format_prompt(request, topic, model_config, grammar_file)

            # Generate text
            response = await self.client.generate(
                model=model_to_use,
                prompt=formatted_prompt,
                stream=request.stream,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                timeout=NetworkConfig.DEFAULT_TIMEOUT,
                json_mode=json_mode,
                grammar_file=grammar_file
            )

            # Post-process response text (fix JSON if needed)
            response_text = self._post_process_response(response.text, grammar_file)

            # Execute backend command if topic has backend configured
            backend_result = await self._execute_backend_command(
                topic, topic_id, response_text
            )

            # Mark processing complete
            end_time = datetime.now()
            elapsed_ms = (end_time - start_time).total_seconds() * 1000
            self.last_command_storage["status"] = "complete"
            self.last_command_storage["end_time"] = end_time
            self.last_command_storage["elapsed_ms"] = elapsed_ms
            self.last_command_storage["success"] = True

            # Update timing breakdown
            timing = self.last_command_storage.get("timing", {})
            timing["llm_end_time"] = end_time.isoformat()

            # Calculate total end-to-end time if we have wake word time
            if timing.get("wake_word_time"):
                try:
                    wake_time = datetime.fromisoformat(timing["wake_word_time"])
                    total_e2e_ms = (end_time - wake_time).total_seconds() * 1000
                    timing["total_end_to_end_ms"] = total_e2e_ms
                    logger.info(f"Command completed: ORAC Core={elapsed_ms:.1f}ms, End-to-End={total_e2e_ms:.1f}ms")
                except Exception as e:
                    logger.warning(f"Could not calculate end-to-end time: {e}")
                    logger.info(f"Command completed in {elapsed_ms:.1f}ms")
            else:
                logger.info(f"Command completed in {elapsed_ms:.1f}ms")

            self.last_command_storage["timing"] = timing

            return GenerationResponse(
                status="success",
                response=response_text,
                elapsed_ms=elapsed_ms,
                model=model_to_use  # Return the actual model used
            )

        except HTTPException as e:
            # Mark processing as error
            end_time = datetime.now()
            elapsed_ms = (end_time - start_time).total_seconds() * 1000
            self.last_command_storage["status"] = "error"
            self.last_command_storage["end_time"] = end_time
            self.last_command_storage["elapsed_ms"] = elapsed_ms
            self.last_command_storage["error"] = str(e.detail)
            raise
        except Exception as e:
            # Mark processing as error
            end_time = datetime.now()
            elapsed_ms = (end_time - start_time).total_seconds() * 1000
            self.last_command_storage["status"] = "error"
            self.last_command_storage["end_time"] = end_time
            self.last_command_storage["elapsed_ms"] = elapsed_ms
            self.last_command_storage["error"] = str(e)
            logger.error(f"Error generating text: {e}")
            if "timed out" in str(e):
                raise HTTPException(status_code=504, detail="Generation timed out")
            raise HTTPException(status_code=500, detail=str(e))

    def _resolve_grammar_file(
        self,
        request: GenerationRequest,
        topic,
        topic_id: str
    ) -> Optional[str]:
        """Resolve which grammar file to use (request > backend > topic static)."""
        # Check for grammar file in request first
        grammar_file = request.grammar_file

        if not grammar_file and topic.backend_id:
            # Topic is linked to a backend - use backend-generated grammar
            backend = self.backend_manager.get_backend(topic.backend_id)

            if not backend:
                raise HTTPException(
                    status_code=404,
                    detail=f"Linked backend '{topic.backend_id}' not found for topic '{topic_id}'"
                )

            # Check if backend is connected
            if not backend.get("status", {}).get("connected"):
                logger.warning(f"Backend '{topic.backend_id}' is not connected")

            # Get or generate grammar for the backend using the injected grammar generator
            grammar_path = self.backend_grammar_generator.get_grammar_file_path(topic.backend_id)

            if not grammar_path.exists():
                # Auto-generate grammar if missing
                logger.info(f"Auto-generating grammar for backend '{topic.backend_id}'")
                result = self.backend_grammar_generator.generate_and_save_grammar(topic.backend_id)
                if not result["success"]:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to generate grammar for backend: {result['error']}"
                    )

            grammar_file = str(grammar_path)
            logger.info(f"Using backend-generated grammar for topic '{topic_id}': {grammar_file}")

        # Fallback to static grammar if configured (backward compatibility)
        elif not grammar_file and topic.grammar.enabled and topic.grammar.file:
            grammar_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data", "grammars", topic.grammar.file
            )
            if os.path.exists(grammar_path):
                grammar_file = grammar_path
                logger.info(f"Using static grammar from topic configuration: {topic.grammar.file}")

        # Validate grammar file exists
        if grammar_file and not os.path.exists(grammar_file):
            logger.warning(f"Grammar file not found: {grammar_file}")
            grammar_file = None

        return grammar_file

    def _parse_grammar_options(self, grammar_file: str) -> Dict[str, list]:
        """Parse GBNF grammar file to extract device and location options."""
        options = {"devices": [], "locations": [], "actions": []}
        try:
            with open(grammar_file, 'r') as f:
                content = f.read()

            # Parse device ::= "option1" | "option2" | ...
            device_match = re.search(r'device\s*::=\s*(.+?)(?:\n|$)', content)
            if device_match:
                devices = re.findall(r'"([^"]+)"', device_match.group(1))
                options["devices"] = [d for d in devices if d != "UNKNOWN"]

            # Parse location ::= "option1" | "option2" | ...
            location_match = re.search(r'location\s*::=\s*(.+?)(?:\n|$)', content)
            if location_match:
                locations = re.findall(r'"([^"]+)"', location_match.group(1))
                options["locations"] = [l for l in locations if l != "UNKNOWN"]

            # Parse action ::= "option1" | "option2" | ...
            action_match = re.search(r'action\s*::=\s*(.+?)(?:\n|$)', content)
            if action_match:
                actions = re.findall(r'"([^"]+)"', action_match.group(1))
                options["actions"] = [a for a in actions if a != "UNKNOWN"]

            logger.debug(f"Parsed grammar options: {options}")
        except Exception as e:
            logger.warning(f"Failed to parse grammar file: {e}")

        return options

    def _format_prompt(
        self,
        request: GenerationRequest,
        topic,
        model_config: Dict[str, Any],
        grammar_file: Optional[str]
    ) -> str:
        """Format the prompt based on grammar file, topic, and model settings."""
        if grammar_file and os.path.exists(grammar_file):
            # Parse grammar to get available options
            grammar_options = self._parse_grammar_options(grammar_file)
            devices = grammar_options.get("devices", [])
            locations = grammar_options.get("locations", [])

            # Get user's custom prompt prefix from topic settings (defaults to standard instruction)
            user_prompt_prefix = topic.settings.system_prompt.strip() if topic.settings.system_prompt else ""

            # Default prefix if none provided
            if not user_prompt_prefix:
                user_prompt_prefix = "/no_think Match input to JSON."

            # Build auto-generated grammar hint
            if devices or locations:
                devices_str = ", ".join(devices) if devices else "UNKNOWN"
                locations_str = ", ".join(locations) if locations else "UNKNOWN"
                grammar_hint = f"Devices: [{devices_str}]. Locations: [{locations_str}]. Use UNKNOWN if no match."
                logger.info(f"Built grammar hint with devices={devices}, locations={locations}")
            else:
                # Fallback if parsing failed
                grammar_hint = "Output JSON with device, action, location. Use UNKNOWN if unclear."

            # Combine user prefix + auto-generated grammar hint
            system_prompt = f"{user_prompt_prefix} {grammar_hint}"
            logger.info(f"Combined prompt: prefix='{user_prompt_prefix}' + grammar_hint")

            # Start the JSON structure to give the model a clear starting point
            formatted_prompt = f"{system_prompt}\n\nUser: {request.prompt}\nAssistant: {{\"device\":\""
        else:
            # Use the standard prompt format for non-grammar requests
            prompt_format = model_config.get("prompt_format", {})
            template = prompt_format.get("template", "{system_prompt}\n\n{user_prompt}")

            # Use JSON-specific system prompt when in JSON mode
            if request.json_mode:
                system_prompt = "You must respond with valid JSON only. Do not include any explanations, thinking, or commentary outside the JSON structure. Your response should be clean, properly formatted JSON that directly answers the request."
            else:
                # Use provided system prompt, then topic's, then model's default
                system_prompt = request.system_prompt or topic.settings.system_prompt or model_config.get("system_prompt", "")

            # Add /no_think prefix if configured in topic
            if topic.settings.no_think and not system_prompt.startswith("/no_think"):
                system_prompt = "/no_think\n\n" + system_prompt

            # Format the prompt using the template
            formatted_prompt = template.format(
                system_prompt=system_prompt,
                user_prompt=request.prompt
            )

        return formatted_prompt

    def _post_process_response(self, response_text: str, grammar_file: Optional[str]) -> str:
        """Post-process response text to ensure valid JSON for grammar-based generation."""
        if grammar_file and os.path.exists(grammar_file):
            # The model response should complete the JSON, but we need to ensure it's properly closed
            if not response_text.strip().endswith('}'):
                # Try to find the end of the JSON structure
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group()
                else:
                    # If no complete JSON found, try to close it properly
                    response_text = response_text.strip()
                    if not response_text.endswith('"'):
                        response_text += '"'
                    if not response_text.endswith('}'):
                        response_text += '}'

        return response_text

    async def _execute_backend_command(
        self,
        topic,
        topic_id: str,
        response_text: str
    ) -> Optional[Dict[str, Any]]:
        """Execute command through backend if topic has backend configured."""
        backend_result = None

        if topic.backend_id and response_text:
            try:
                # Parse the JSON response
                try:
                    parsed_json = json.loads(response_text)
                    self.last_command_storage["generated_json"] = parsed_json
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse generated JSON: {e}")
                    parsed_json = None

                if parsed_json:
                    # Get backend instance (backend encapsulates dispatcher internally)
                    backend = self.backend_manager.create_backend_instance(topic.backend_id)

                    if backend:
                        logger.info(f"Using backend '{topic.backend_id}' dispatcher for topic '{topic_id}'")

                        # Execute through backend's internal dispatcher
                        backend_result = await backend.dispatch_command(parsed_json, {'topic': topic.dict()})

                        # Store backend execution details
                        self.last_command_storage["backend_id"] = topic.backend_id
                        self.last_command_storage["backend_result"] = backend_result
                        self.last_command_storage["success"] = backend_result.get("success", False)

                        if backend_result.get("error"):
                            logger.error(f"Backend execution failed: {backend_result['error']}")
                        else:
                            logger.info(f"Backend execution successful")
                    else:
                        logger.warning(f"Backend '{topic.backend_id}' could not be instantiated")

            except Exception as e:
                logger.error(f"Failed to execute through backend: {e}")
                self.last_command_storage["error"] = str(e)
                self.last_command_storage["success"] = False

        return backend_result
