#!/usr/bin/env python3
"""
VAgent Setup Script

Automated setup and configuration for the VAgent system.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        sys.exit(1)
    logger.info(f"Python {sys.version_info.major}.{sys.version_info.minor} detected")


def create_directories():
    """Create required directories."""
    directories = [
        'vagent_results',
        'vagent_cache',
        'logs',
        'config',
        'data',
        'videos'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")


def install_dependencies():
    """Install required Python packages."""
    logger.info("Installing dependencies...")
    
    try:
        # Upgrade pip
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        
        # Install requirements
        requirements_file = Path(__file__).parent / "requirements.txt"
        if requirements_file.exists():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)], 
                          check=True, capture_output=True)
            logger.info("Dependencies installed successfully")
        else:
            logger.warning("requirements.txt not found, skipping dependency installation")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        logger.info("You may need to install dependencies manually:")
        logger.info(f"pip install -r {requirements_file}")
        sys.exit(1)


def setup_configuration():
    """Setup default configuration files."""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Copy default config if it doesn't exist
    default_config = Path(__file__).parent / "config" / "default.yaml"
    user_config = config_dir / "user_config.yaml"
    
    if not user_config.exists() and default_config.exists():
        import shutil
        shutil.copy2(default_config, user_config)
        logger.info(f"Created default configuration: {user_config}")
    
    # Create environment template
    env_template = Path(__file__).parent / "config" / ".env.template"
    if env_template.exists():
        shutil.copy2(env_template, ".env.template")
        logger.info("Created environment template: .env.template")


def check_api_keys():
    """Check for required API keys."""
    required_keys = [
        'VAGENT_AI_API_KEY',
        'VAGENT_EXA_API_KEY',
        'VAGENT_FIRECRAWL_API_KEY'
    ]
    
    missing_keys = []
    for key in required_keys:
        if key not in os.environ:
            missing_keys.append(key)
    
    if missing_keys:
        logger.warning(f"Missing environment variables: {', '.join(missing_keys)}")
        logger.info("Please set these environment variables or add them to your .env file")
        
        # Create .env file with template
        env_file = Path(".env")
        if not env_file.exists():
            with open(env_file, 'w') as f:
                f.write("# VAgent Environment Variables\n")
                f.write("# Add your API keys here:\n")
                for key in required_keys:
                    f.write(f"{key}=\n")
            logger.info("Created .env template file")
    else:
        logger.info("All required API keys are set")


def verify_installation():
    """Verify the installation is working correctly."""
    logger.info("Verifying installation...")
    
    try:
        # Test imports
        from vagent.core import VAgentOrchestrator
        from vagent.utils import load_config, validate_config
        
        # Test configuration loading
        config = load_config()
        if not validate_config(config):
            logger.error("Configuration validation failed")
            return False
        
        # Test orchestrator initialization
        orchestrator = VAgentOrchestrator()
        logger.info("VAgent orchestrator initialized successfully")
        
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


def create_sample_scripts():
    """Create sample scripts for common use cases."""
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    # Create quick start script
    quick_start_script = scripts_dir / "quick_start.py"
    if not quick_start_script.exists():
        quick_start_content = '''#!/usr/bin/env python3
"""
VAgent Quick Start Script

Run a basic VAgent pipeline with minimal configuration.
"""

import asyncio
import logging
from vagent.core import VAgentOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Run a quick start pipeline."""
    logger.info("Starting VAgent quick start...")
    
    # Initialize orchestrator
    orchestrator = VAgentOrchestrator()
    
    # Run a small pipeline for testing
    results = await orchestrator.run_full_pipeline(
        research_websites=100,    # Small number for testing
        top_trends=10,           # Few trends for testing
        videos_per_topic=2,      # Few videos per topic
        target_platforms=["youtube"]  # Single platform for testing
    )
    
    logger.info(f"Quick start completed! Created {len(results.get('video_contents', []))} videos")
    
    # Save results
    output_file = orchestrator.save_results(results, "quick_start_results.json")
    logger.info(f"Results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        with open(quick_start_script, 'w') as f:
            f.write(quick_start_content)
        
        # Make script executable
        quick_start_script.chmod(0o755)
        logger.info(f"Created quick start script: {quick_start_script}")
    
    # Create research-only script
    research_script = scripts_dir / "research_only.py"
    if not research_script.exists():
        research_content = '''#!/usr/bin/env python3
"""
VAgent Research-Only Script

Run only the web research phase.
"""

import asyncio
import logging
from vagent.core import VAgentOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Run research-only pipeline."""
    logger.info("Starting VAgent research-only...")
    
    # Initialize orchestrator
    orchestrator = VAgentOrchestrator()
    
    # Run research phase only
    results = await orchestrator.run_research_only(500)  # 500 websites for testing
    
    logger.info(f"Research completed! Found {len(results)} results")
    
    # Save results
    output_file = orchestrator.save_results({'research_results': results}, "research_results.json")
    logger.info(f"Results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        with open(research_script, 'w') as f:
            f.write(research_content)
        
        # Make script executable
        research_script.chmod(0o755)
        logger.info(f"Created research-only script: {research_script}")


def main():
    """Main setup function."""
    print("🚀 VAgent Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    install_dependencies()
    
    # Setup configuration
    setup_configuration()
    
    # Check API keys
    check_api_keys()
    
    # Create sample scripts
    create_sample_scripts()
    
    # Verify installation
    if verify_installation():
        print("\n✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Set your API keys in the .env file")
        print("2. Review and customize config/user_config.yaml")
        print("3. Run a quick test:")
        print("   python scripts/quick_start.py")
        print("4. Run the full pipeline:")
        print("   python vagent/main.py --websites 1000 --trends 50 --videos-per-topic 5")
    else:
        print("\n❌ Setup verification failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()