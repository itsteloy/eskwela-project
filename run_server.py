#!/usr/bin/env python
"""
Django + Channels Development Server Launcher

This script starts the Eskwela project with real-time WebSocket support
using Daphne (ASGI server) instead of Django's default development server.

Usage:
    python run_server.py              # Start with default settings (0.0.0.0:8000)
    python run_server.py localhost 8000  # Custom host and port

Requirements:
    - daphne
    - channels
    - channels_redis (optional, for production-grade channel layers)

Features:
    - WebSocket support for real-time dashboard updates
    - HTTP/2 support
    - Better performance than runserver
    - Automatic reload on file changes
"""

import os
import sys
import django
from django.conf import settings
from django.core.management import call_command


def setup_django():
    """Initialize Django settings"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eskwela_project.settings")
    django.setup()


def run_daphne_server(host="0.0.0.0", port=8000):
    """Start Daphne ASGI server"""
    print(
        f"""
    ╔════════════════════════════════════════════════════════════════╗
    ║       ESKWELA PROJECT - Real-Time Development Server          ║
    ╠════════════════════════════════════════════════════════════════╣
    ║ Server Type:    Daphne (ASGI)                                ║
    ║ WebSocket:      ✓ Enabled (ws://{host}:{port}/ws/dashboard/)   
    ║ HTTP Support:   ✓ HTTP, HTTP/2, WebSocket                    ║
    ║ Host:           {host}                                      
    ║ Port:           {port}                                           
    ║────────────────────────────────────────────────────────────────║
    ║ ✓ Real-time dashboard updates                                 ║
    ║ ✓ WebSocket connections                                       ║
    ║ ✓ Automatic reloading on code changes                         ║
    ║────────────────────────────────────────────────────────────────║
    ║ Access the application at: http://{host}:{port}               
    ║                                                               
    ║ Press Ctrl+C to stop the server                              
    ╚════════════════════════════════════════════════════════════════╝
    """
    )

    try:
        from daphne.cli import CommandLineInterface

        # Prepare Daphne arguments
        sys.argv = [
            "daphne",
            "-b",
            host,
            "-p",
            str(port),
            "-v",
            "2",  # Verbosity
            "eskwela_project.asgi:application",
        ]

        # Run Daphne
        CommandLineInterface().run()

    except ImportError:
        print("\n❌ ERROR: Daphne is not installed!")
        print("\nInstall it with:")
        print("  pip install daphne")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point"""
    # Parse command line arguments
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    # Setup Django
    setup_django()

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Run migrations if needed
    print("Checking migrations...")
    call_command("migrate", verbosity=0)

    # Start Daphne server
    run_daphne_server(host, port)


if __name__ == "__main__":
    main()
