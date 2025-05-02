# Background:
We are building a Ollama based API which pauses natural language commands and turns them into well formatted Jason. The target device is an Nvidia orange nano 8 GB. We are running in docker using docker compose.


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

