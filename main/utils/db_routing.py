import logging

from peewee import DatabaseProxy, PostgresqlDatabase, SqliteDatabase

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
        self.proxy = DatabaseProxy()
        self._db = None

    def connect(self, **kwargs):
        if self._db is not None:
            logging.warning("Database is already connected.")
            return self._db

        local = kwargs.get("local", True)

        try:
            if local:
                db_path = kwargs.get("path", "main.db")
                self._db = SqliteDatabase(db_path)
                logging.info(f"Connected to the local database: {db_path}")
            else:
                self._db = PostgresqlDatabase(
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

            self.proxy.initialize(self.db)
            self._db.connect()
            return self._db

        except Exception as e:
            logging.exception("Failed to connect to the database.")
            raise e

    def close(self):
        if self._db:
            self._db.close()
            self._db = None
            self.proxy.initialize(None)
            logging.info("Database connection closed.")

    @property
    def db(self):
        """Get the actual database instance (not the proxy)"""
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db


db_manager = DatabaseManager()
