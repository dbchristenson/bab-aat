import logging

from peewee import PostgresqlDatabase, SqliteDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("main/logs/db_routing.log"),  # Log to a file
        logging.StreamHandler(),  # Log to the console
    ],
)


class DatabaseManager:
    def __init__(self):
        self.db = None

    def connect(self, **kwargs):
        local = kwargs.get("local", True)

        try:
            if local:
                db_path = kwargs.get("path", "main.db")
                self.db = SqliteDatabase(db_path)
                logging.info(f"Connected to the local database: {db_path}")
            else:
                self.db = PostgresqlDatabase(
                    dbname=kwargs["dbname"],
                    user=kwargs["user"],
                    password=kwargs["password"],
                    host=kwargs["host"],
                    port=kwargs["port"],
                )
                logging.info(
                    (
                        f"Connected remote database: {kwargs['db_name']} at "
                        f"{kwargs['host']}:{kwargs['port']}"
                    )
                )

            self.db.connect()
            return self.db

        except Exception as e:
            logging.exception("Failed to connect to the database.")
            raise e

    def close(self):
        if self.db:
            self.db.close()
            logging.info("Database connection closed.")


db_manager = DatabaseManager()
