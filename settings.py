from datetime import timedelta

sqlite_file_name = "database.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

TOKEN_ACTIVE_TIME = timedelta(hours=3)
