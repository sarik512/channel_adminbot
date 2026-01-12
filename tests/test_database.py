import os
import importlib
import tempfile

import database as db


def test_basic_db_operations(tmp_path):
    # Use a temporary database file
    db_path = str(tmp_path / "test.db")
    os.environ['DATABASE_FILE'] = db_path

    # Reload module to pick up env var
    importlib.reload(db)

    # Init DB
    db.init_db()

    # Add admin and channel
    assert db.add_admin(12345, username='testadmin')
    assert db.add_channel('@testchannel', 'Test Channel')

    # Assign admin to channel
    assert db.assign_admin_to_channel(12345, '@testchannel')

    # Log upload
    assert db.log_upload(12345, '@testchannel', 'Test Title', 1, 1, file_id='file_1', message_id='msg_1')

    # Stats
    stats = db.get_admin_stats(12345)
    assert stats['total'] == 1
    assert stats['by_channel'][0]['count'] == 1

    ch_stats = db.get_channel_stats('@testchannel')
    assert ch_stats['total'] == 1
    assert ch_stats['by_admin'][0]['count'] == 1
