#!/usr/bin/env python3
"""
Test client for the Voice Service
"""

import argparse
import json
import asyncio
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
import httpx

# Constants
DEFAULT_URL = "http://localhost:8000"
TIMEOUT = 90.0  # Generous timeout for model loading

# Sample commands to test
SAMPLE_COMMANDS = [
    "Turn on the kitchen lights",
    "Set the living room thermostat to 72 degrees",
    "Turn off all lights in the house",
    "Play some music in the bedroom",
    "Open the garage door",
    "Close the blinds in the office"
]

console = Console()

async def get_models(base_url):
    """Get list of available models"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{base_url}/models")
        if response.status_code == 200:
            return response.json()
        else:
            console.print(f"[red]Error getting models: {response.text}[/red]")
            return []

async def get_memory_info(base_url):
    """Get memory info"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(f"{base_url}/memory")
        if response.status_code == 200:
            return response.json()
        else:
            console.print(f"[red]Error getting memory info: {response.text}[/red]")
            return {}

async def load_model(base_url, model_id):
    """Load a specific model"""
    console.print(f"[yellow]Loading model {model_id}...[/yellow]")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Use the new GET endpoint instead of the POST route with path parameter
        response = await client.get(f"{base_url}/load-model?model_id={model_id}")
        if response.status_code == 200:
            console.print(f"[green]Model {model_id} loaded successfully[/green]")
            return True
        else:
            console.print(f"[red]Error loading model {model_id}: {response.text}[/red]")
            return False

async def unload_model(base_url, model_id):
    """Unload a specific model"""
    console.print(f"[yellow]Unloading model {model_id}...[/yellow]")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Use the new GET endpoint instead of the POST route with path parameter
        response = await client.get(f"{base_url}/unload-model?model_id={model_id}")
        if response.status_code == 200:
            console.print(f"[green]Model {model_id} unloaded successfully[/green]")
            return True
        else:
            console.print(f"[red]Error unloading model {model_id}: {response.text}[/red]")
            return False

async def send_command(base_url, prompt, model_id=None, temperature=0.3, max_tokens=100):
    """Send a command to the API"""
    request = {
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    if model_id:
        request["model_id"] = model_id
    
    start_time = time.time()
    console.print(f"[cyan]Sending command:[/cyan] {prompt}")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(f"{base_url}/smart-home/command", json=request)
            
            elapsed = time.time() - start_time
            if response.status_code == 200:
                result = response.json()
                
                # Format the command JSON nicely if it exists
                command_json = result.get('command')
                if command_json:
                    command_str = json.dumps(command_json, indent=2)
                else:
                    command_str = "None"
                
                # Print the result
                console.print(Panel(
                    f"[bold]Command JSON:[/bold]\n{command_str}\n\n"
                    f"[bold]Raw Output:[/bold]\n{result.get('raw_generation', 'No output')}\n\n"
                    f"[bold]Model Used:[/bold] {result.get('model_used', 'Unknown')}\n"
                    f"[bold]Error:[/bold] {result.get('error', 'None')}\n"
                    f"[bold]Time:[/bold] {elapsed:.2f} seconds",
                    title="Response",
                    border_style="green" if command_json else "red"
                ))
                return result
            else:
                console.print(f"[red]Error (Status {response.status_code}):[/red] {response.text}")
                return None
        except httpx.ReadTimeout:
            console.print("[red]Request timed out. The model might be loading or the server is busy.[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Error sending command: {str(e)}[/red]")
            return None

async def display_models(base_url):
    """Display all available models"""
    models = await get_models(base_url)
    
    if not models:
        console.print("[yellow]No models available[/yellow]")
        return
    
    table = Table(title="Available Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Type", style="magenta")
    
    for model in models:
        status = "Current & Loaded" if model["is_current"] else ("Loaded" if model["is_loaded"] else "Not Loaded")
        table.add_row(
            model["model_id"],
            status,
            model.get("model_type", "Unknown")
        )
    
    console.print(table)

async def display_memory(base_url):
    """Display memory information"""
    memory = await get_memory_info(base_url)
    
    if not memory:
        console.print("[yellow]Memory information not available[/yellow]")
        return
    
    table = Table(title="Memory Information")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total RAM", f"{memory.get('total_ram', 0):.2f} GB")
    table.add_row("Available RAM", f"{memory.get('available_ram', 0):.2f} GB")
    table.add_row("Used RAM", f"{memory.get('used_ram', 0):.2f} GB")
    table.add_row("RAM Usage", f"{memory.get('ram_percent', 0):.1f}%")
    
    if memory.get('total_gpu') is not None:
        table.add_row("Total GPU Memory", f"{memory.get('total_gpu', 0):.2f} GB")
        table.add_row("Used GPU Memory", f"{memory.get('used_gpu', 0):.2f} GB")
        table.add_row("GPU Usage", f"{memory.get('gpu_percent', 0):.1f}%")
    
    console.print(table)

async def interactive_mode(base_url):
    """Run in interactive mode"""
    console.print(Panel("""Interactive Mode
    Commands:
    - Type any text to send as a smart home command
    - 'exit' to quit
    - 'models' to list models
    - 'memory' to show memory info
    - 'load <model_id>' to load a specific model
    - 'unload <model_id>' to unload a model
    """, border_style="blue"))
    
    while True:
        command = console.input("[bold blue]Enter command:[/bold blue] ")
        
        if command.lower() == 'exit':
            break
        elif command.lower() == 'models':
            await display_models(base_url)
        elif command.lower() == 'memory':
            await display_memory(base_url)
        elif command.lower().startswith('load '):
            model_id = command[5:].strip()
            await load_model(base_url, model_id)
        elif command.lower().startswith('unload '):
            model_id = command[7:].strip()
            await unload_model(base_url, model_id)
        else:
            await send_command(base_url, command)

async def test_models(base_url):
    """Test multiple models with the same command"""
    test_command = "Turn on the kitchen lights"
    console.print(Panel(f"Testing Different Models with: '{test_command}'", border_style="blue"))
    
    # Test with different models
    for model_id in ["distilgpt2", "gpt2", "tinyllama"]:
        console.print(f"\n[bold cyan]Testing with model: {model_id}[/bold cyan]")
        
        # Load model
        success = await load_model(base_url, model_id)
        if not success:
            console.print(f"[red]Skipping model {model_id} due to loading failure[/red]")
            continue
            
        # Send test command
        await send_command(base_url, test_command, model_id=model_id)
        
        # Optional: unload to save memory
        # await unload_model(base_url, model_id)

def main():
    parser = argparse.ArgumentParser(description="Test client for Voice Service API")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Base URL of the API (default: {DEFAULT_URL})")
    parser.add_argument("--model", help="Specify model to use")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--test-models", action="store_true", help="Test with different models")
    parser.add_argument("command", nargs="?", help="Command to send (if not in interactive mode)")
    
    args = parser.parse_args()
    
    async def run():
        if args.interactive:
            await interactive_mode(args.url)
        elif args.test_models:
            await test_models(args.url)
        elif args.command:
            await send_command(args.url, args.command, model_id=args.model)
        else:
            print("No command provided. Use --interactive for interactive mode or provide a command.")
    
    asyncio.run(run())

if __name__ == "__main__":
    main()
