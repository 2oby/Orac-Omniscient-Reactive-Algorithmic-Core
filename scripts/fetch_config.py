#!/usr/bin/env python3
"""
Configuration management script for ORAC.

This script handles:
1. Fetching the latest configuration from Git
2. Pulling configuration from test machines (orin/orin2)
3. Updating local configuration files

Usage:
    python fetch_config.py [--from-git] [--from-test-machine MACHINE]
    
    Options:
        --from-git              Fetch latest config from Git
        --from-test-machine     Pull config from test machine (orin/orin2)
"""

import argparse
import asyncio
import os
import shutil
import subprocess
from pathlib import Path
import logging
from typing import Optional, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration paths and files
CONFIG_PATHS = {
    "homeassistant": Path(__file__).parent.parent / "orac" / "homeassistant",
    "data": Path(__file__).parent.parent / "data"
}

CONFIG_FILES = {
    "homeassistant": [
        "config.yaml",
    ],
    "data": [
        "model_configs.yaml",
        "grammars.yaml",
        "favorites.json"
    ]
}

async def fetch_from_git() -> bool:
    """Fetch latest configuration from Git."""
    try:
        # Check if we're in a git repository
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error("Not in a git repository")
            return False

        # Fetch latest changes
        logger.info("Fetching latest changes from Git...")
        subprocess.run(["git", "fetch", "origin"], check=True)
        
        # Reset config files to their state in origin/main
        for dir_name, files in CONFIG_FILES.items():
            dir_path = CONFIG_PATHS[dir_name]
            for config_file in files:
                file_path = dir_path / config_file
                if file_path.exists():
                    logger.info(f"Resetting {config_file} to origin/main...")
                    subprocess.run(
                        ["git", "checkout", "origin/main", "--", str(file_path)],
                        check=True
                    )
        
        logger.info("Successfully updated configuration from Git")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

async def fetch_from_test_machine(machine: str) -> bool:
    """Pull configuration from test machine."""
    if machine not in ["orin", "orin2"]:
        logger.error(f"Invalid machine name: {machine}")
        return False
        
    try:
        # Create backup of current config
        for dir_name, files in CONFIG_FILES.items():
            dir_path = CONFIG_PATHS[dir_name]
            backup_dir = dir_path / "backup"
            backup_dir.mkdir(exist_ok=True)
            timestamp = subprocess.check_output(
                ["date", "+%Y%m%d_%H%M%S"],
                text=True
            ).strip()
            
            for config_file in files:
                src = dir_path / config_file
                if src.exists():
                    dst = backup_dir / f"{config_file}.{timestamp}"
                    shutil.copy2(src, dst)
        
        # Pull config files from test machine
        logger.info(f"Pulling configuration from {machine}...")
        
        for dir_name, files in CONFIG_FILES.items():
            remote_dir = f"{machine}:~/orac/{dir_path.relative_to(Path(__file__).parent.parent)}/"
            for config_file in files:
                remote_file = f"{remote_dir}{config_file}"
                local_file = CONFIG_PATHS[dir_name] / config_file
                
                # Use rsync to pull the file
                result = subprocess.run(
                    ["rsync", "-avz", remote_file, str(local_file)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Failed to pull {config_file}: {result.stderr}")
                    return False
                else:
                    logger.info(f"Successfully pulled {config_file}")
        
        logger.info("Successfully updated configuration from test machine")
        return True
        
    except Exception as e:
        logger.error(f"Error pulling from test machine: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser(description="Fetch and update ORAC configuration")
    parser.add_argument(
        "--from-git",
        action="store_true",
        help="Fetch latest config from Git"
    )
    parser.add_argument(
        "--from-test-machine",
        choices=["orin", "orin2"],
        help="Pull config from test machine"
    )
    
    args = parser.parse_args()
    
    if not (args.from_git or args.from_test_machine):
        parser.print_help()
        return
    
    success = True
    if args.from_git:
        success &= await fetch_from_git()
    
    if args.from_test_machine:
        success &= await fetch_from_test_machine(args.from_test_machine)
    
    if not success:
        logger.error("Configuration update failed")
        exit(1)
    
    logger.info("Configuration update completed successfully")

if __name__ == "__main__":
    asyncio.run(main()) 