"""
Grammar Scheduler for Home Assistant Integration.

This module handles scheduled grammar updates and validation,
including daily updates at 3am and manual triggers with validation.

IMPORTANT: The HA-generated grammar is saved to ha_grammar.gbnf for reference,
but the system uses the static default.gbnf grammar file for production LLM calls.
This keeps the system simple and avoids complexity from dynamic grammar changes.
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional, Dict, Any
from .grammar_manager import HomeAssistantGrammarManager
from .mapping_config import EntityMappingConfig
from .client import HomeAssistantClient

logger = logging.getLogger(__name__)

class GrammarScheduler:
    """Scheduler for grammar updates with validation."""
    
    def __init__(self, grammar_manager: HomeAssistantGrammarManager, 
                 mapping_config: EntityMappingConfig,
                 client: HomeAssistantClient):
        """Initialize the grammar scheduler.
        
        Args:
            grammar_manager: Grammar manager instance
            mapping_config: Entity mapping configuration
            client: Home Assistant client
        """
        self.grammar_manager = grammar_manager
        self.mapping_config = mapping_config
        self.client = client
        self.scheduler_task: Optional[asyncio.Task] = None
        self.last_update: Optional[datetime] = None
        self.update_time = time(3, 0)  # 3:00 AM
        
        logger.info("GrammarScheduler initialized with daily update at 3:00 AM")
    
    async def start_scheduler(self) -> None:
        """Start the daily scheduler."""
        if self.scheduler_task and not self.scheduler_task.done():
            logger.warning("Scheduler already running")
            return
        
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Grammar scheduler started")
    
    async def stop_scheduler(self) -> None:
        """Stop the daily scheduler."""
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("Grammar scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs daily at 3am."""
        while True:
            try:
                now = datetime.now()
                next_run = self._get_next_run_time()
                
                # Calculate sleep time until next run
                sleep_seconds = (next_run - now).total_seconds()
                if sleep_seconds > 0:
                    logger.info(f"Next grammar update scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    await asyncio.sleep(sleep_seconds)
                
                # Run the update
                logger.info("Running scheduled grammar update...")
                await self.update_grammar_with_validation()
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)
    
    def _get_next_run_time(self) -> datetime:
        """Get the next scheduled run time."""
        now = datetime.now()
        next_run = datetime.combine(now.date(), self.update_time)
        
        # If it's already past 3am today, schedule for tomorrow
        if now.time() >= self.update_time:
            next_run = next_run.replace(day=next_run.day + 1)
        
        return next_run
    
    async def update_grammar_with_validation(self, force_update: bool = False) -> Dict[str, Any]:
        """Update grammar with validation and test generation.
        
        Args:
            force_update: Force update even if recently updated
            
        Returns:
            Dictionary with update results and validation status
        """
        start_time = datetime.now()
        logger.info("Starting grammar update with validation...")
        
        try:
            # Check if we need to update (unless forced)
            if not force_update and self.last_update:
                time_since_update = (start_time - self.last_update).total_seconds()
                if time_since_update < 3600:  # Less than 1 hour ago
                    logger.info("Grammar was recently updated, skipping")
                    return {
                        "status": "skipped",
                        "message": "Grammar was recently updated",
                        "last_update": self.last_update.isoformat(),
                        "validation": "not_required"
                    }
            
            # Step 1: Run auto-discovery to get latest entities
            logger.info("Step 1: Running auto-discovery...")
            await self.mapping_config.auto_discover_entities()
            
            # Step 2: Update grammar with latest data
            logger.info("Step 2: Updating grammar...")
            await self.grammar_manager.update_grammar(run_auto_discovery=False)  # Already done above
            
            # Step 3: Generate new GBNF grammar
            logger.info("Step 3: Generating GBNF grammar...")
            gbnf_content = await self.grammar_manager.generate_gbnf_grammar(force_regenerate=True)
            
            # Step 4: Save to ha_grammar.gbnf (not default.gbnf to keep things simple)
            logger.info("Step 4: Saving HA-generated grammar to ha_grammar.gbnf...")
            grammar_file = await self.grammar_manager.save_gbnf_grammar("data/test_grammars/ha_grammar.gbnf")
            
            # Step 5: Validate grammar with test generation
            logger.info("Step 5: Validating grammar with test generation...")
            validation_result = await self._validate_grammar(grammar_file)
            
            # Update last update time
            self.last_update = datetime.now()
            
            # Get grammar statistics
            grammar_stats = self.grammar_manager.get_grammar_stats()
            
            result = {
                "status": "success",
                "message": "Grammar updated and validated successfully",
                "grammar_file": grammar_file,
                "validation": validation_result,
                "grammar_stats": grammar_stats,
                "update_time": self.last_update.isoformat(),
                "elapsed_seconds": (datetime.now() - start_time).total_seconds()
            }
            
            logger.info(f"Grammar update completed successfully in {result['elapsed_seconds']:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error during grammar update: {e}")
            return {
                "status": "error",
                "message": f"Grammar update failed: {str(e)}",
                "error": str(e),
                "update_time": datetime.now().isoformat(),
                "elapsed_seconds": (datetime.now() - start_time).total_seconds()
            }
    
    async def _validate_grammar(self, grammar_file: str) -> Dict[str, Any]:
        """Validate grammar by testing generation with a sample prompt.
        
        Args:
            grammar_file: Path to the grammar file to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Import here to avoid circular imports
            from orac.llama_cpp_client import LlamaCppClient
            import os
            
            # Test prompt
            test_prompt = "Turn on the Kitchen lights"
            
            # Get default model
            from orac.config import load_favorites
            favorites = load_favorites()
            default_model = favorites.get("default_model")
            
            if not default_model:
                return {
                    "status": "warning",
                    "message": "No default model configured, skipping validation",
                    "test_prompt": test_prompt,
                    "response": None
                }
            
            # Create client for validation
            model_path = os.getenv("ORAC_MODELS_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models/gguf"))
            client = LlamaCppClient(model_path=model_path)
            
            # Test generation with the HA-generated grammar (for validation only, not for production use)
            response = await client.generate(
                model=default_model,
                prompt=test_prompt,
                temperature=0.1,
                top_p=0.9,
                top_k=10,
                max_tokens=50,
                grammar_file=grammar_file
            )
            
            # Validate response format
            import json
            try:
                # Try to parse as JSON
                json_response = json.loads(response.text)
                
                # Check for required fields
                required_fields = ["device", "action", "location"]
                missing_fields = [field for field in required_fields if field not in json_response]
                
                if missing_fields:
                    return {
                        "status": "error",
                        "message": f"Generated response missing required fields: {missing_fields}",
                        "test_prompt": test_prompt,
                        "response": response.text,
                        "parsed_json": json_response
                    }
                
                return {
                    "status": "success",
                    "message": "Grammar validation successful",
                    "test_prompt": test_prompt,
                    "response": response.text,
                    "parsed_json": json_response,
                    "response_time": response.response_time
                }
                
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "message": f"Generated response is not valid JSON: {e}",
                    "test_prompt": test_prompt,
                    "response": response.text
                }
                
        except Exception as e:
            logger.error(f"Error during grammar validation: {e}")
            return {
                "status": "error",
                "message": f"Grammar validation failed: {str(e)}",
                "test_prompt": test_prompt,
                "response": None
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status.
        
        Returns:
            Dictionary with scheduler status information
        """
        return {
            "scheduler_running": self.scheduler_task is not None and not self.scheduler_task.done(),
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "next_update": self._get_next_run_time().isoformat(),
            "update_time": self.update_time.strftime("%H:%M")
        } 