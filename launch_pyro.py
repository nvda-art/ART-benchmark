#!/usr/bin/env python
import argparse
import logging
import sys
import time
import Pyro4
from implementations.pyro_impl import BenchmarkService

def run_server(name):
    """
    Run a Pyro4 server with the BenchmarkService
    
    Args:
        name: The name to register in the Pyro name server
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    
    # Create and start the Pyro4 daemon
    daemon = Pyro4.Daemon()
    uri = daemon.register(BenchmarkService)
    
    # Register with the name server
    try:
        ns = Pyro4.locateNS()
        ns.register(name, uri)
        logging.info(f"Registered Pyro service as {name}")
    except Exception as e:
        logging.error(f"Failed to register with name server: {e}")
        logging.info(f"Pyro service available at: {uri}")
        sys.exit(1)
    
    # Signal that we're ready
    print(f"READY - Pyro service registered as {name}", flush=True)
    sys.stdout.flush()
    
    # Start the request loop
    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        logging.info("Server shutting down")
    except Exception as e:
        logging.error(f"Error in request loop: {e}")
    finally:
        # Clean up
        if daemon:
            daemon.shutdown()
        try:
            ns = Pyro4.locateNS()
            ns.remove(name)
            logging.info(f"Removed {name} from name server")
        except Exception as e:
            logging.warning(f"Could not remove from name server: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, default="example.benchmark.service", 
                        help="Name to register in the Pyro name server")
    args = parser.parse_args()
    run_server(args.name)
