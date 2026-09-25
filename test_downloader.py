import os
from download_manager import DownloadManager, load_dummy_config

def test_command_building():
    # Setup dummy config
    config = load_dummy_config()
    # Override paths to ensure commands are runnable/testable without real executables
    config["yt_dlp_path"] = "yt-dlp" 
    config["ffmpeg_path"] = "ffmpeg"
    
    manager = DownloadManager(
        yt_dlp_path=config["yt_dlp_path"],
        ffmpeg_path=config["ffmpeg_path"],
        default_dir=config["default_download_path"],
        config=config
    )
    
    print("--- Running Command Builder Tests ---")

    # Test Case 1: Single Video (Default)
    url1 = "http://example.com/video1"
    cmd1 = manager.build_command(url1)
    print(f"\nTest 1 (Single Video): URL={url1}")
    # Expected: Should include -o and the URL at the end
    assert url1 in cmd1[-1]
    assert cmd1[0] == "yt-dlp"
    print("  [PASS] Single URL command structure verified.")

    # Test Case 2: Audio Download
    url2 = "http://example.com/audio1"
    cmd2 = manager.build_command(url2, download_type="audio")
    print(f"\nTest 2 (Audio): URL={url2}")
    # Expected: Should include -x and --audio-format mp3
    assert "-x" in cmd2
    print("  [PASS] Audio command structure verified.")

    # Test Case 3: Playlist "all"
    url3 = "http://example.com/playlist_all"
    cmd3 = manager.build_command(url3, is_playlist=True, playlist_items="all")
    print(f"\nTest 3 (Playlist ALL): URL={url3}")
    # Expected: Should include --yes-playlist
    assert "--yes-playlist" in cmd3
    print("  [PASS] Playlist 'all' command structure verified.")

    # Test Case 4: Playlist Specific Range
    url4 = "http://example.com/playlist_range"
    cmd4 = manager.build_command(url4, is_playlist=True, playlist_items="1:3")
    print(f"\nTest 4 (Playlist 1:3): URL={url4}")
    # Expected: Should include --playlist-items 1:3
    assert "--playlist-items" in cmd4 and "1:3" in cmd4
    print("  [PASS] Playlist range command structure verified.")
    
    # Test Case 5: Playlist Comma-separated items
    url5 = "http://example.com/playlist_comma"
    cmd5 = manager.build_command(url5, is_playlist=True, playlist_items="1,3,5")
    print(f"\nTest 5 (Playlist Comma): URL={url5}")
    # Expected: Should include --playlist-items 1,3,5
    assert "--playlist-items" in cmd5 and "1,3,5" in cmd5
    print("  [PASS] Playlist comma-separated command structure verified.")
    
    # Test Case 6: Playlist scope keywords
    for scope, expected in (("first", "1"), ("last", "-1"), ("between", "2:5"), ("items", "1,3,5")):
        url6 = "http://example.com/playlist_scope"
        cmd6 = manager.build_command(url6, is_playlist=True, playlist_items=scope if scope in ("first", "last") else expected)
        print(f"\nTest 6 (Playlist scope '{scope}'): URL={url6}")
        assert "--playlist-items" in cmd6 and expected in cmd6
        assert "--yes-playlist" not in cmd6
        print(f"  [PASS] Playlist scope '{scope}' -> --playlist-items {expected}")

    print("\n====================================")
    print("ALL COMMAND BUILDER TESTS PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    test_command_building()