import subprocess
import unittest
from unittest import mock

import warper


LOUDNORM_STDERR = """
Input #0, wav, from '/tmp/in.wav':
  Duration: 00:00:10.00, bitrate: 1411 kb/s
[Parsed_loudnorm_0 @ 0x123456]
{
    "input_i" : "-18.30",
    "input_tp" : "-2.10",
    "input_lra" : "4.50",
    "input_thresh" : "-28.00",
    "output_i" : "-14.00",
    "output_tp" : "-1.00",
    "output_lra" : "4.20",
    "output_thresh" : "-23.80",
    "normalization_type" : "dynamic",
    "target_offset" : "-0.10"
}
"""


class LoudnormHelperTests(unittest.TestCase):
    def test_extract_loudnorm_stats_reads_measurement_json(self):
        stats = warper._extract_loudnorm_stats(LOUDNORM_STDERR)

        self.assertEqual(stats["input_i"], "-18.30")
        self.assertEqual(stats["input_tp"], "-2.10")
        self.assertEqual(stats["target_offset"], "-0.10")

    @mock.patch("warper.subprocess.run")
    @mock.patch("warper.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_master_audio_runs_two_pass_loudnorm_for_mp3(self, which_mock, run_mock):
        run_mock.side_effect = [
            subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr=LOUDNORM_STDERR),
            subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr=""),
        ]

        warper.master_audio("/tmp/in.wav", "/tmp/out.mp3")

        self.assertEqual(run_mock.call_count, 2)

        first_command = run_mock.call_args_list[0].args[0]
        second_command = run_mock.call_args_list[1].args[0]
        second_filter = second_command[second_command.index("-af") + 1]

        self.assertIn("print_format=json", first_command[first_command.index("-af") + 1])
        self.assertEqual(first_command[-3:], ["-f", "null", "-"])
        self.assertIn("measured_I=-18.30", second_filter)
        self.assertIn("measured_TP=-2.10", second_filter)
        self.assertIn("offset=-0.10", second_filter)
        self.assertIn("libmp3lame", second_command)
        self.assertEqual(second_command[-1], "/tmp/out.mp3")
        which_mock.assert_called_once_with("ffmpeg")

    @mock.patch("warper.subprocess.run")
    @mock.patch("warper.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_master_audio_uses_pcm_output_for_wav(self, which_mock, run_mock):
        run_mock.side_effect = [
            subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr=LOUDNORM_STDERR),
            subprocess.CompletedProcess(args=["ffmpeg"], returncode=0, stdout="", stderr=""),
        ]

        warper.master_audio("/tmp/in.wav", "/tmp/out.wav")

        second_command = run_mock.call_args_list[1].args[0]
        self.assertIn("pcm_s16le", second_command)
        self.assertNotIn("libmp3lame", second_command)
        self.assertEqual(second_command[-1], "/tmp/out.wav")
        which_mock.assert_called_once_with("ffmpeg")

    @mock.patch("warper.shutil.which", return_value=None)
    def test_master_audio_fails_fast_when_ffmpeg_is_missing(self, which_mock):
        with self.assertRaisesRegex(RuntimeError, "ffmpeg not found"):
            warper.master_audio("/tmp/in.wav", "/tmp/out.mp3")

        which_mock.assert_called_once_with("ffmpeg")


if __name__ == "__main__":
    unittest.main()
