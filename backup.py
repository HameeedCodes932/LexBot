"""
Backup script for LexBot — database-only (pg_dump).

Usage:
  python backup.py                          # default output dir: ./backups/
  python backup.py --output /path/to/backups

Requirements:
  - pg_dump must be installed and on PATH
  - DATABASE_URL must be set in .env
"""

import argparse
import datetime
import logging
import os
import subprocess
import tarfile
import tempfile

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backup")


def parse_db_url(url: str):
    if not url:
        return None
    rest = url
    if rest.startswith("postgresql+asyncpg://"):
        rest = "postgresql://" + rest[len("postgresql+asyncpg://"):]
    elif rest.startswith("postgresql://"):
        pass
    else:
        return None

    parts = rest.split("://", 1)[1]
    user_pass, rest = parts.split("@", 1) if "@" in parts else ("", parts)
    username, password = user_pass.split(":", 1) if ":" in user_pass else (user_pass, "")
    host_port, database = rest.split("/", 1) if "/" in rest else (rest, "")
    host, port = host_port.split(":", 1) if ":" in host_port else (host_port, "5432")
    return {"host": host, "port": port, "username": username, "password": password, "database": database}


def backup_postgres(db_info: dict, output_dir: str) -> str:
    dump_path = os.path.join(output_dir, "lexbot_db.sql")
    env = os.environ.copy()
    env["PGPASSWORD"] = db_info["password"]

    cmd = [
        "pg_dump",
        "-h", db_info["host"],
        "-p", db_info["port"],
        "-U", db_info["username"],
        "-d", db_info["database"],
        "-f", dump_path,
        "--no-owner", "--no-acl",
    ]
    logger.info("Running pg_dump: %s", " ".join(cmd))
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("pg_dump failed: %s", result.stderr)
        raise RuntimeError(f"pg_dump failed: {result.stderr}")
    logger.info("Database dumped to %s", dump_path)
    return dump_path


def create_archive(output_dir: str, files: list[str]) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"lexbot_backup_{timestamp}.tar.gz"
    archive_path = os.path.join(output_dir, archive_name)

    files = [f for f in files if f]
    if not files:
        logger.warning("No files to archive.")
        return ""

    with tarfile.open(archive_path, "w:gz") as tar:
        for f in files:
            tar.add(f, arcname=os.path.basename(f))

    logger.info("Archive created: %s", archive_path)
    return archive_path


def main():
    parser = argparse.ArgumentParser(description="LexBot data backup")
    parser.add_argument("--output", default="backups", help="Output directory (default: ./backups)")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    temp_dir = tempfile.mkdtemp(prefix="lexbot_backup_")
    db_dump = ""

    try:
        db_url = os.getenv("DATABASE_URL", "")
        db_info = parse_db_url(db_url)
        if db_info:
            db_dump = backup_postgres(db_info, temp_dir)
        else:
            logger.warning("DATABASE_URL not set or invalid — skipping database backup.")

        archive = create_archive(output_dir, [db_dump])
        if archive:
            print(f"\nBackup complete: {archive}")
        else:
            print("\nNo backup was created.")
    finally:
        for p in [db_dump]:
            if p and os.path.isfile(p):
                os.remove(p)
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
