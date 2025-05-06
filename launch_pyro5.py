#!/usr/bin/env python
import argparse
import logging
import sys
import time
import signal  # Import signal module for handling termination
import Pyro5.api
import Pyro5.errors
from implementations.pyro5_impl import BenchmarkService # Import from the new pyro5 implementation

# Global variables for signal handling
daemon_instance = None
ns_instance = None
registered_name = None

def handle_shutdown_signal(sig, frame):
    """Gracefully shut down the server on SIGINT or SIGTERM."""
    global daemon_instance, ns_instance, registered_name
    logging.info(f"Received signal {sig}, shutting down...")
    if ns_instance and registered_name:
        try:
            logging.info(f"Removing '{registered_name}' from name server...")
            ns_instance.remove(registered_name)
            logging.info(f"Removed '{registered_name}' successfully.")
        except Pyro5.errors.NamingError as e:
            logging.warning(f"Could not remove '{registered_name}' from name server (maybe already gone?): {e}")
        except Exception as e:
            logging.error(f"Error removing '{registered_name}' from name server: {e}")

    if daemon_instance:
        logging.info("Shutting down Pyro5 daemon...")
        # Daemon shutdown should ideally be quick
        try:
            # Use a separate thread to avoid potential deadlocks if shutdown blocks
            shutdown_thread = threading.Thread(target=daemon_instance.shutdown)
            shutdown_thread.start()
            shutdown_thread.join(timeout=5.0) # Wait max 5 seconds for shutdown
            if shutdown_thread.is_alive():
                logging.warning("Daemon shutdown took too long.")
            else:
                logging.info("Daemon shutdown complete.")
        except Exception as e:
            logging.error(f"Error during daemon shutdown: {e}")
        daemon_instance = None # Clear instance

    logging.info("Exiting.")
    sys.exit(0)


def run_server(name):
    """
    Run a Pyro5 server with the BenchmarkService

    Args:
        name: The name to register in the Pyro name server
    """
    global daemon_instance, ns_instance, registered_name
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    registered_name = name # Store for signal handler

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    # Create and start the Pyro5 daemon
    try:
        daemon_instance = Pyro5.api.Daemon()
        uri = daemon_instance.register(BenchmarkService, name) # Register the CLASS
        logging.info(f"Pyro5 daemon created on {daemon_instance.locationStr}")
        logging.info(f"Registered BenchmarkService class as '{name}'")
    except Exception as e:
        logging.exception("Failed to create Pyro5 daemon or register service")
        sys.exit(1)

    # Register with the name server
    try:
        logging.info("Locating Pyro5 Name Server...")
        ns_instance = Pyro5.api.locate_ns()
        logging.info(f"Found Name Server at {ns_instance._pyroUri}")
        logging.info(f"Registering '{name}' --> {uri}")
        ns_instance.register(name, uri)
        logging.info(f"Successfully registered '{name}' in Name Server.")
    except Pyro5.errors.NamingError as e:
        logging.error(f"Failed to locate or register with Pyro5 Name Server: {e}")
        logging.warning("Service will be available via direct URI only.")
        # Decide if we should exit or continue without NS
        # For benchmark consistency, let's exit if NS registration fails
        if daemon_instance: daemon_instance.shutdown()
        sys.exit(1)
    except Exception as e:
        logging.exception("An unexpected error occurred during Name Server interaction")
        if daemon_instance: daemon_instance.shutdown()
        sys.exit(1)

    # Signal that we're ready - IMPORTANT for launch_and_wait
    print(f"READY - Pyro5 service registered as {name}", flush=True)
    sys.stdout.flush()

    # Start the request loop
    try:
        logging.info("Starting Pyro5 request loop...")
        daemon_instance.requestLoop()
    except Exception as e:
        logging.exception("Error in request loop")
    finally:
        logging.info("Request loop finished.")
        # Final cleanup attempt (might be redundant if signal handler ran)
        handle_shutdown_signal(0, None) # Call handler manually if loop exits unexpectedly

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pyro5 Benchmark Service Launcher")
    parser.add_argument("--name", type=str, default="example.benchmark.pyro5.service",
                        help="Name to register in the Pyro5 name server")
    args = parser.parse_args()
    run_server(args.name)
