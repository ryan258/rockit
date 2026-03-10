import json
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path

import rr_converter


class CleanChartTests(unittest.TestCase):
    def test_clean_chart_removes_duplicates_limits_hammer_and_speed(self):
        notes = [
            {"_time": 1.0, "_lineIndex": 0, "_lineLayer": 1, "_type": 0, "_cutDirection": 1},
            {"_time": 1.0, "_lineIndex": 0, "_lineLayer": 1, "_type": 0, "_cutDirection": 1},
            {"_time": 1.0, "_lineIndex": 1, "_lineLayer": 1, "_type": 0, "_cutDirection": 1},
            {"_time": 1.0, "_lineIndex": 3, "_lineLayer": 1, "_type": 0, "_cutDirection": 1},
            {"_time": 1.05, "_lineIndex": 2, "_lineLayer": 1, "_type": 0, "_cutDirection": 1},
            {"_time": 1.2, "_lineIndex": 1, "_lineLayer": 1, "_type": 0, "_cutDirection": 1},
        ]

        cleaned = rr_converter.clean_chart(notes, min_time_delta=0.125, hammer_limit=2)

        self.assertEqual(
            [(note["_time"], note["_lineIndex"]) for note in cleaned],
            [(1.0, 0), (1.0, 3), (1.2, 1)],
        )


class MetricsTests(unittest.TestCase):
    def test_compute_average_nps_and_rank(self):
        notes = [{"_time": 1.0, "_lineIndex": 0}] * 6

        nps = rr_converter.compute_average_nps(notes, 2.0)

        self.assertEqual(nps, 3.0)
        self.assertEqual(rr_converter.nps_to_difficulty_rank(nps), 6)

    def test_detect_song_duration_seconds_reads_wav_length(self):
        with tempfile.TemporaryDirectory() as workspace:
            audio_path = Path(workspace) / "fixture.wav"
            self._write_silence_wav(audio_path, duration_seconds=2.0)

            duration = rr_converter.detect_song_duration_seconds(str(audio_path))

            self.assertAlmostEqual(duration, 2.0, places=2)

    def _write_silence_wav(self, audio_path: Path, duration_seconds: float) -> None:
        sample_rate = 8000
        frame_count = int(sample_rate * duration_seconds)
        with wave.open(str(audio_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(b"\x00\x00" * frame_count)


class ConverterFixtureTests(unittest.TestCase):
    def test_fixture_zip_converts_and_packages_all_difficulties(self):
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            zip_path = workspace_path / "fixture.zip"
            extract_path = workspace_path / "extract"
            output_path = workspace_path / "output"

            self._write_fixture_zip(zip_path)

            info, difficulty_sets, base_dir = rr_converter.extract_bs_data(str(zip_path), str(extract_path))
            duration_seconds = rr_converter.detect_song_duration_seconds(str(extract_path / "song.wav"))
            rr_difficulty_sets = rr_converter.build_rr_difficulty_sets(
                difficulty_sets,
                min_time_delta=0.125,
                hammer_limit=2,
                song_duration_seconds=duration_seconds,
            )
            rr_converter.package_rr_song(base_dir, str(output_path), info, rr_difficulty_sets)

            with open(output_path / "info.dat", "r", encoding="utf-8") as handle:
                info_data = json.load(handle)
            with open(output_path / "Level1.json", "r", encoding="utf-8") as handle:
                level_1 = json.load(handle)
            with open(output_path / "Level2.json", "r", encoding="utf-8") as handle:
                level_2 = json.load(handle)
            with open(output_path / "Level3.json", "r", encoding="utf-8") as handle:
                level_3 = json.load(handle)

            self.assertEqual(info_data["_songName"], "Fixture Song")
            self.assertEqual(info_data["_beatsPerMinute"], 128)
            self.assertEqual(info_data["_songApproximativeDuration"], 2)
            self.assertTrue((output_path / "song.wav").exists())
            self.assertTrue((output_path / "cover.jpg").exists())
            self.assertEqual(len(info_data["_difficultyBeatmapSets"]), 1)
            difficulty_maps = info_data["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"]
            self.assertEqual(
                [
                    (
                        entry["_difficulty"],
                        entry["_difficultyRank"],
                        entry["_beatmapFilename"],
                    )
                    for entry in difficulty_maps
                ],
                [
                    ("Normal", 2, "Level1.json"),
                    ("Hard", 2, "Level2.json"),
                    ("Expert", 3, "Level3.json"),
                ],
            )
            self.assertEqual(
                [(note["_time"], note["_lineIndex"]) for note in level_1["_notes"]],
                [(1.0, 0), (1.0, 3)],
            )
            self.assertEqual(
                [(note["_time"], note["_lineIndex"]) for note in level_2["_notes"]],
                [(2.0, 1), (2.2, 2)],
            )
            self.assertEqual(
                [(note["_time"], note["_lineIndex"]) for note in level_3["_notes"]],
                [(3.0, 0), (3.0, 3), (3.2, 1)],
            )

    def test_main_returns_nonzero_for_missing_zip(self):
        self.assertEqual(rr_converter.main(["/tmp/definitely-missing-rockit-fixture.zip"]), 1)

    def _write_fixture_zip(self, zip_path: Path) -> None:
        info = {
            "_songFilename": "song.wav",
            "_coverImageFilename": "cover.jpg",
            "_songName": "Fixture Song",
            "_songSubName": "",
            "_songAuthorName": "Fixture Artist",
            "_beatsPerMinute": 128,
            "_difficultyBeatmapSets": [
                {
                    "_beatmapCharacteristicName": "Standard",
                    "_difficultyBeatmaps": [
                        {
                            "_difficulty": "Normal",
                            "_difficultyRank": 3,
                            "_beatmapFilename": "Normal.dat",
                            "_noteJumpMovementSpeed": 10,
                            "_noteJumpStartBeatOffset": 0,
                        },
                        {
                            "_difficulty": "Hard",
                            "_difficultyRank": 5,
                            "_beatmapFilename": "Hard.dat",
                            "_noteJumpMovementSpeed": 14,
                            "_noteJumpStartBeatOffset": 0.5,
                        },
                        {
                            "_difficulty": "Expert",
                            "_difficultyRank": 7,
                            "_beatmapFilename": "Expert.dat",
                            "_noteJumpMovementSpeed": 18,
                            "_noteJumpStartBeatOffset": 1,
                        }
                    ]
                }
            ],
        }
        normal_beatmap = {
            "_notes": [
                {"_time": 1.0, "_lineIndex": 0},
                {"_time": 1.0, "_lineIndex": 0},
                {"_time": 1.0, "_lineIndex": 2},
                {"_time": 1.0, "_lineIndex": 3},
                {"_time": 1.05, "_lineIndex": 1},
            ]
        }
        hard_beatmap = {
            "_notes": [
                {"_time": 2.0, "_lineIndex": 1},
                {"_time": 2.05, "_lineIndex": 2},
                {"_time": 2.2, "_lineIndex": 2},
            ]
        }
        expert_beatmap = {
            "_notes": [
                {"_time": 3.0, "_lineIndex": 0},
                {"_time": 3.0, "_lineIndex": 3},
                {"_time": 3.1, "_lineIndex": 2},
                {"_time": 3.2, "_lineIndex": 1},
            ]
        }
        audio_bytes = self._build_silence_wav_bytes(duration_seconds=2.0)

        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("Info.dat", json.dumps(info))
            archive.writestr("Normal.dat", json.dumps(normal_beatmap))
            archive.writestr("Hard.dat", json.dumps(hard_beatmap))
            archive.writestr("Expert.dat", json.dumps(expert_beatmap))
            archive.writestr("song.wav", audio_bytes)
            archive.writestr("cover.jpg", b"fixture-cover")

    def _build_silence_wav_bytes(self, duration_seconds: float) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".wav") as handle:
            self._write_silence_wav(Path(handle.name), duration_seconds)
            handle.seek(0)
            return handle.read()

    def _write_silence_wav(self, audio_path: Path, duration_seconds: float) -> None:
        sample_rate = 8000
        frame_count = int(sample_rate * duration_seconds)
        with wave.open(str(audio_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(b"\x00\x00" * frame_count)


if __name__ == "__main__":
    unittest.main()
