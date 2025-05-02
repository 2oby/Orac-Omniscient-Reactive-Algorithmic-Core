# ORAC Voice Service Optimization Report
Executive Summary
The ORAC (Omniscient Reactive Algorithmic Core) voice service running on the NVIDIA Jetson Orin Nano 8GB is experiencing performance issues, with slow response times and suboptimal natural language to JSON conversion results. This report outlines a comprehensive optimization strategy focused on model selection, resource management, and code enhancements to significantly improve performance while maintaining functionality.
Current System Analysis
Hardware Configuration

Device: NVIDIA Jetson Orin Nano 8GB
Memory: 8GB shared between system and GPU
Storage: Limited local storage (NVMe recommended)
Docker Configuration: 6GB memory limit, NVIDIA runtime enabled

# Software Stack

Base Image: nvcr.io/nvidia/l4t-ml.2.0-py3
Framework: FastAPI, Transformers, PyTorch
Models: Multiple models cached including TinyLlama, distilgpt2, QWen models
Purpose: Conversion of natural language commands to structured JSON for smart home control

# Identified Issues

Resource Constraints: The 8GB of shared memory is insufficient for efficiently running multiple models
Model Loading/Unloading: Inefficient switching between models consumes valuable resources
Performance Bottlenecks: Non-optimized models running too slowly for practical use
Result Quality: Suboptimal JSON output generation from voice commands
Memory Management: Poor memory handling leads to excessive resource consumption



# Folder structure on target device:
toby@ubuntu:~/voice_service$ pwd
/home/toby/voice_service
toby@ubuntu:~/voice_service$ ls
config  deploy.sh  docker-compose.yml  Dockerfile  logs  models  README.md  response_to_JSON_integration.py  test_client.py  voice_service.py
toby@ubuntu:~/voice_service$ ls config
model_configs.yaml  prompt_distilgpt2.txt  prompt_llama.txt       prompt_tinyllama_tinyllama_1_1b_chat_v1_0.txt
prompt_default.txt  prompt_gpt2.txt        prompt_qwen3_1_7b.txt  validation.yaml
toby@ubuntu:~/voice_service$ ls models
cache
toby@ubuntu:~/voice_service$ ls models/cache
models--distilgpt2              models--microsoft--phi-2         models--Qwen--Qwen3-0.6B      models--Qwen--Qwen3-1.7B-FP8
models--EleutherAI--pythia-70m  models--nilq--mistral-1L-tiny    models--Qwen--Qwen3-0.6B-FP8  models--TinyLlama--TinyLlama-1.1B-Chat-v1.0
models--gpt2                    models--Qwen--Qwen1.5-0.5B-Chat  models--Qwen--Qwen3-1.7B
toby@ubuntu:~/voice_service$ 

# Status
The application is working but the results are disappointing and it seems quite slow. I am in the process of testing the various models to see which work best.



# ToDo:

## Optimization Strategy
1. Model Selection & Rationalization
Recommended Models to Keep & Use:

TinyLlama/TinyLlama-1.1B-Chat-v1.0: Good balance of size and performance for edge devices
nilq/mistral-1L-tiny: Ultra-lightweight model suitable for simple command parsing
microsoft/phi-2: Efficient model with strong reasoning capabilities
Qwen3-0.6B-Q4_K_M.gguf (397 MB): Quantized version from unsloth/Qwen3-0.6B-GGUF
Qwen3-1.7B-Q4_K_M.gguf (1.4 GB): Larger quantized model from unsloth/Qwen3-1.7B-GGUF

Model Acquisition Steps:

Delete all other model files from the models/cache directory to free up space
Download the Qwen3 GGUF models using:
bashmkdir -p /home/toby/voice_service/models/gguf
cd /home/toby/voice_service/models/gguf
wget https://huggingface.co/unsloth/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf
wget https://huggingface.co/unsloth/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf


2. Hardware & System Optimization
Power Management

Implement Jetson power mode optimization in the deployment script:
bash# Add to deploy.sh before starting the service
ssh orin "sudo nvpmodel -m 0" # Set to maximum performance mode
ssh orin "sudo jetson_clocks" # Max out clock speeds


Storage Optimization

Add NVMe SSD storage for model files and Docker volumes
Mount the NVMe drive to /home/toby/voice_service/models for faster loading

Docker Configuration Updates

Update docker-compose.yml with optimized resource settings:
yamlservices:
  voice:
    # ... existing configuration ...
    deploy:
      resources:
        limits:
          memory: 7g
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    shm_size: 2g
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - TRANSFORMERS_CACHE=/models/cache
      - GGUF_MODELS_DIR=/models/gguf


3. Code Optimizations
Memory Management

Implement more aggressive garbage collection after model unloading
Add explicit CUDA cache clearing
Optimize tokenizer loading with shared vocabulary

Model Loading System

Prioritize quantized models when available
Implement a smarter model selection strategy based on command complexity
Add warm-up inference to avoid first-query latency

GGUF Model Support

Add support for GGUF format models using llama.cpp integration
Implement a class to handle both Hugging Face and GGUF model loading:
pythonclass ModelLoader:
    def load_gguf_model(self, model_path):
        # GGUF model loading implementation
        pass
    
    def load_hf_model(self, model_id):
        # HF model loading with quantization
        pass


JSON Extraction Enhancement

Rewrite the JSON extraction logic for better accuracy
Add JSON schema validation and automatic correction
Create a feedback mechanism to improve extraction over time

4. Prompt Engineering Improvements
Command-Specific Templates

Create specialized prompt templates for different command types:

Lighting commands
Temperature control
Entertainment systems
Multi-device commands



Enhanced Prompt Format

Structure prompts to better guide the model output:
<system>
You are a smart home control system. Convert the user's natural language command to JSON.
Follow this JSON format: {"device": string, "location": string, "action": string, "value": string}
Provide ONLY the JSON output with no explanation.
</system>

<user>
{command}
</user>

<assistant>


5. Quantization & Optimization
Model Quantization

Implement 4-bit quantization for compatible models
Add dynamic quantization during model loading
Use optimized kernels for NVIDIA hardware

Performance Monitoring

Add performance metrics collection
Implement token generation speed tracking
Create an automated benchmarking system for model comparison

Implementation Plan
Phase 1: Foundation (1-2 days)

Clean up model directory
Download recommended quantized models
Update docker-compose.yml with optimized settings
Implement power management settings

Phase 2: Code Enhancements (3-5 days)

Add GGUF model support
Improve memory management
Optimize model loading/unloading
Enhance JSON extraction logic

Phase 3: Prompt Engineering (2-3 days)

Create specialized prompt templates
Optimize instruction formats
Test with various command types

Phase 4: Performance Tuning (3-4 days)

Implement quantization optimizations
Add performance monitoring
Fine-tune resource allocation
Benchmark and compare models

Expected Outcomes
After implementing these optimizations, the ORAC voice service should experience:

2-5x improvement in response time
More accurate JSON output generation
Reduced memory consumption
More consistent performance
Better handling of complex commands

Conclusion
The current ORAC voice service implementation on the Jetson Orin Nano 8GB has significant potential for improvement through model rationalization, resource optimization, and code enhancements. By focusing on a select group of quantized models and implementing the recommended optimizations, the service can achieve substantially better performance and reliability.
The next step is to begin implementing Phase 1 of the plan, followed by performance testing to validate the improvements before proceeding to subsequent phases.