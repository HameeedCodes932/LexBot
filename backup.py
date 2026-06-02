"""
Backup script for LexBot.

Creates:
  1. PostgreSQL dump of the main database (via pg_dump)
  2. Snapshot of the ChromaDB vector store directory
  3. Single compressed archive (.tar.gz) with timestamp

Usage:
  python backup.py                          # default output dir: ./backups/
  python backup.py --output /path/to/backups
  python backup.py --db-only                # database only, skip ChromaDB
  python backup.py --chroma-only            # ChromaDB only, skip database

Requirements:
  - pg_dump must be installed and on PATH
  - DATABASE_URL must be set in .env
"""

import argparse
import datetime
import logging
import os
import subprocess
import sys
import tarfile
import tempfile
import shutil

from dotenv import load_dotenv

import config

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("backup")


def parse_db_url(url: str):
    """Parse DATABASE_URL into pg_dump-compatible parts."""
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
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "database": database,
    }


def backup_postgres(db_info: dict, output_dir: str) -> str:
    """Run pg_dump and return the path to the dump file."""
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
        "--no-owner",
        "--no-acl",
    ]
    logger.info("Running pg_dump: %s", " ".join(cmd))
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("pg_dump failed: %s", result.stderr)
        raise RuntimeError(f"pg_dump failed: {result.stderr}")
    logger.info("Database dumped to %s", dump_path)
    return dump_path


def backup_chromadb(chroma_dir: str, output_dir: str) -> str:
    """Copy ChromaDB directory and return the path."""
    if not os.path.isdir(chroma_dir):
        logger.warning("ChromaDB directory not found: %s — skipping", chroma_dir)
        return ""

    dest = os.path.join(output_dir, "chroma_db")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(chroma_dir, dest)
    logger.info("ChromaDB copied to %s", dest)
    return dest


def create_archive(output_dir: str, files: list[str]) -> str:
    """Compress all backup files into a single tar.gz."""
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


def clean_temp_files(*paths):
    for p in paths:
        if p and os.path.isfile(p):
            os.remove(p)
        elif p and os.path.isdir(p):
            shutil.rmtree(p)


def main():
    parser = argparse.ArgumentParser(description="LexBot data backup")
    parser.add_argument("--output", default="backups", help="Output directory (default: ./backups)")
    parser.add_argument("--db-only", action="store_true", help="Backup database only")
    parser.add_argument("--chroma-only", action="store_true", help="Backup ChromaDB only")
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    temp_dir = tempfile.mkdtemp(prefix="lexbot_backup_")
    db_dump = ""
    chroma_copy = ""

    try:
        db_url = os.getenv("DATABASE_URL", "")
        db_info = parse_db_url(db_url)

        if not args.chroma_only:
            if db_info:
                db_dump = backup_postgres(db_info, temp_dir)
            else:
                logger.warning("DATABASE_URL not set or invalid — skipping database backup.")

        if not args.db_only:
            chroma_copy = backup_chromadb(config.CHROMA_DIR, temp_dir)

        archive = create_archive(output_dir, [db_dump, chroma_copy])
        if archive:
            print(f"\n✅ Backup complete: {archive}")
        else:
            print("\n⚠️  Backup completed but no archive was created (no data to back up).")
    finally:
        clean_temp_files(db_dump, chroma_copy)
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
