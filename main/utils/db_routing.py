import logging
from typing import Any, Optional

import psycopg2
from peewee import SqliteDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("main/logs/db_routing.log"),  # Log to a file
        logging.StreamHandler(),  # Log to the console
    ],
)


def connect_to_db(**kwargs) ->Optional[Any]:
    """
    Connect to the database based on the local flag.
    If local is True, connect to the local database.
    If local is False, connect to the remote database.

    Args:
        local (bool): Flag to indicate local or remote connection.
        **kwargs: Additional arguments for connection parameters.
            - if local is True:
                - path (str): Path to the local database.
            - if local is False:
                - db_name (str): Name of the remote database.
                - user (str): Username for the remote database.
                - password (str): Password for the remote database.
                - host (str): Hostname of the remote database.
                - port (int): Port number of the remote database.
    """
    local = kwargs.get("local", True)

    try:
        if local and "path" in kwargs:
            db_path = kwargs.get("path")
            db = SqliteDatabase(db_path)
            logging.info(f"Connected to the {'local' if local else 'remote'} database: {db_path}")
            return db.connect()

        elif local and "path" not in kwargs:
            raise ValueError("When local is True, 'path' must be provided in kwargs.")

        else:
            required_params = ["db_name", "user", "password", "host", "port"]
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"For remote connection, missing required parameter: {param}")

            return psycopg2.connect(
                dbname=kwargs["db_name"],
                user=kwargs["user"],
                password=kwargs["password"],
                host=kwargs["host"],
                port=kwargs["port"],
            )

    except Exception as e:
        logging.exception("Failed to connect to the database.")
        raise e