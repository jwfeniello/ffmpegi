"""Tests for CLI — request/file splitting, output path derivation, and main()."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from cli import split_request_and_files, main, MEDIA_EXTS
from output_path import derive_output_path
from models import EditPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plan(**kwargs) -> EditPlan:
    defaults: dict = {'inputs': [Path('video.mp4')]}
    defaults.update(kwargs)
    return EditPlan(**defaults)


def _mock_check():
    """Patch check_ffmpeg to do nothing."""
    return patch('cli.check_ffmpeg', return_value=None)


# ---------------------------------------------------------------------------
# Token splitting
# ---------------------------------------------------------------------------

class TestSplitRequestAndFiles:
    def test_single_trailing_file_by_ext(self):
        req, files = split_request_and_files(['compress', 'for', 'discord', 'video.mp4'])
        assert req == 'compress for discord'
        assert files == [Path('video.mp4')]

    def test_multiple_trailing_files(self):
        req, files = split_request_and_files(['merge', 'into', 'mkv', 'a.mp4', 'b.mp4'])
        assert req == 'merge into mkv'
        assert files == [Path('a.mp4'), Path('b.mp4')]

    def test_no_files_in_tokens(self):
        req, files = split_request_and_files(['compress', 'for', 'discord'])
        assert req == 'compress for discord'
        assert files == []

    def test_audio_ext_collected(self):
        req, files = split_request_and_files(['rip', 'the', 'audio', 'speech.mkv'])
        assert req == 'rip the audio'
        assert files == [Path('speech.mkv')]

    def test_wav_word_without_dot_not_collected(self):
        # 'wav' has no dot so suffix == '' — should NOT be collected
        req, files = split_request_and_files(['rip', 'audio', 'as', 'wav', 'speech.mkv'])
        assert req == 'rip audio as wav'
        assert files == [Path('speech.mkv')]

    def test_mp4_word_without_dot_not_collected(self):
        req, files = split_request_and_files(['convert', 'to', 'mp4', 'video.avi'])
        assert req == 'convert to mp4'
        assert files == [Path('video.avi')]

    def test_existing_file_without_media_ext_collected(self, tmp_path):
        # A file that exists on disk is collected even without media extension
        f = tmp_path / 'myvideo'
        f.touch()
        req, files = split_request_and_files(['compress', str(f)])
        assert req == 'compress'
        assert files == [f]

    def test_absolute_path_with_media_ext(self):
        req, files = split_request_and_files(['cut', '1:30', '/abs/path/video.mp4'])
        assert req == 'cut 1:30'
        assert files == [Path('/abs/path/video.mp4')]

    def test_empty_tokens(self):
        req, files = split_request_and_files([])
        assert req == ''
        assert files == []

    def test_three_files_for_merge(self):
        req, files = split_request_and_files(
            ['merge', 'these', 'clip1.mp4', 'clip2.mp4', 'clip3.mp4']
        )
        assert req == 'merge these'
        assert len(files) == 3

    def test_request_preserved_with_colons(self):
        # Timestamps in request should not be mistaken for files
        req, files = split_request_and_files(
            ['cut', 'from', '1:30', 'to', '2:45', 'intro.mov']
        )
        assert req == 'cut from 1:30 to 2:45'
        assert files == [Path('intro.mov')]


# ---------------------------------------------------------------------------
# Output path derivation
# ---------------------------------------------------------------------------

class TestDeriveOutputPath:
    def test_trim_only(self):
        plan = _plan(trim_start=0.0, trim_end=30.0)
        assert derive_output_path(plan, Path('video.mp4')) == Path('video_trimmed.mp4')

    def test_resize_only(self):
        plan = _plan(target_resolution='720p')
        assert derive_output_path(plan, Path('video.mkv')) == Path('video_720p.mkv')

    def test_compress_filesize(self):
        plan = _plan(target_filesize_mb=25.0)
        assert derive_output_path(plan, Path('video.mp4')) == Path('video_compressed.mp4')

    def test_compress_preset(self):
        plan = _plan(target_preset='discord')
        assert derive_output_path(plan, Path('video.mp4')) == Path('video_compressed.mp4')

    def test_extract_audio_default_mp3(self):
        plan = _plan(extract_audio=True)
        assert derive_output_path(plan, Path('video.mp4')) == Path('video.mp3')

    def test_extract_audio_wav(self):
        plan = _plan(extract_audio=True, audio_format='wav')
        assert derive_output_path(plan, Path('video.mp4')) == Path('video.wav')

    def test_merge(self):
        plan = _plan(inputs=[Path('a.mp4'), Path('b.mp4')])
        assert derive_output_path(plan, Path('a.mp4')) == Path('merged.mp4')

    def test_merge_with_target_format(self):
        plan = _plan(inputs=[Path('a.mp4'), Path('b.mp4')], target_format='mkv')
        assert derive_output_path(plan, Path('a.mp4')) == Path('merged.mkv')

    def test_trim_plus_convert_uses_target_format(self):
        plan = _plan(trim_start=0.0, trim_end=30.0, target_format='mp4')
        assert derive_output_path(plan, Path('video.mkv')) == Path('video_trimmed.mp4')

    def test_resize_plus_convert_uses_target_format(self):
        plan = _plan(target_resolution='720p', target_format='mp4')
        assert derive_output_path(plan, Path('video.mkv')) == Path('video_720p.mp4')

    def test_compress_plus_convert(self):
        plan = _plan(target_filesize_mb=25.0, target_format='mp4')
        assert derive_output_path(plan, Path('video.mkv')) == Path('video_compressed.mp4')

    def test_trim_priority_over_resize(self):
        plan = _plan(trim_start=0.0, trim_end=30.0, target_resolution='720p')
        assert derive_output_path(plan, Path('video.mp4')) == Path('video_trimmed.mp4')

    def test_trim_priority_over_compress(self):
        plan = _plan(trim_start=0.0, trim_end=30.0, target_filesize_mb=25.0)
        assert derive_output_path(plan, Path('video.mp4')) == Path('video_trimmed.mp4')

    def test_resize_priority_over_compress(self):
        plan = _plan(target_resolution='1080p', target_filesize_mb=25.0)
        assert derive_output_path(plan, Path('video.mp4')) == Path('video_1080p.mp4')

    def test_no_overwrite_guard(self):
        # If input is video.mp3 and extract_audio gives video.mp3, append _out
        plan = _plan(
            inputs=[Path('video.mp3')],
            extract_audio=True,
            audio_format='mp3',
        )
        out = derive_output_path(plan, Path('video.mp3'))
        assert out == Path('video_out.mp3')


# ---------------------------------------------------------------------------
# main() — dry-run, errors, missing file, missing ffmpeg
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_returns_zero(self, tmp_path):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with _mock_check():
            rc = main(['--dry-run', 'compress', str(f)])
        assert rc == 0

    def test_dry_run_prints_ffmpeg_command(self, tmp_path, capsys):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with _mock_check():
            main(['--dry-run', 'compress', str(f)])
        out = capsys.readouterr().out
        assert 'ffmpeg' in out

    def test_dry_run_does_not_run_ffmpeg(self, tmp_path):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with _mock_check(), patch('cli.run_ffmpeg') as mock_run:
            main(['--dry-run', 'compress', str(f)])
        mock_run.assert_not_called()

    def test_explicit_output_path_used(self, tmp_path, capsys):
        f = tmp_path / 'clip.mp4'
        out = tmp_path / 'result.mp4'
        f.touch()
        with _mock_check():
            main(['--dry-run', '-o', str(out), 'compress', str(f)])
        printed = capsys.readouterr().out
        assert str(out) in printed


class TestClarificationError:
    def test_ambiguous_request_exits_1(self, tmp_path, capsys):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with _mock_check():
            rc = main(['--dry-run', 'make it smaller', str(f)])
        assert rc == 1
        assert 'Error:' in capsys.readouterr().err

    def test_error_reason_printed(self, tmp_path, capsys):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with _mock_check():
            main(['--dry-run', 'make it smaller', str(f)])
        err = capsys.readouterr().err
        assert len(err.strip()) > 0

    def test_unrecognised_request_exits_1(self, tmp_path):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with _mock_check():
            rc = main(['--dry-run', 'xyzzy frobulate', str(f)])
        assert rc == 1


class TestMissingFile:
    def test_nonexistent_file_exits_1(self, capsys):
        rc = main(['--dry-run', 'compress', 'ghost.mp4'])
        assert rc == 1
        assert 'not found' in capsys.readouterr().err.lower()

    def test_error_message_includes_path(self, capsys):
        main(['--dry-run', 'compress', 'ghost.mp4'])
        assert 'ghost.mp4' in capsys.readouterr().err


class TestMissingFFmpeg:
    def test_missing_ffmpeg_exits_1(self, tmp_path):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with patch('cli.check_ffmpeg', side_effect=SystemExit('ffmpeg not found')):
            rc = main(['--dry-run', 'compress', str(f)])
        assert rc == 1

    def test_missing_ffmpeg_prints_message(self, tmp_path, capsys):
        f = tmp_path / 'clip.mp4'
        f.touch()
        with patch('cli.check_ffmpeg', side_effect=SystemExit('ffmpeg not found. Install with: winget install Gyan.FFmpeg')):
            main(['--dry-run', 'compress', str(f)])
        assert 'ffmpeg' in capsys.readouterr().err.lower()


class TestNoRequest:
    def test_no_tokens_exits_1(self):
        rc = main([])
        assert rc == 1

    def test_only_file_no_request_exits_1(self, tmp_path):
        f = tmp_path / 'clip.mp4'
        f.touch()
        rc = main([str(f)])
        assert rc == 1
