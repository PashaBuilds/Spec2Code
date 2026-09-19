"""Uretim modu (static/ai) ve yapay zeka modundaki descriptor uretimi (dogrulayici dongusu).

Statik mod: LLM hicbir noktada devreye girmez (llm.enabled olsa bile). Yapay zeka modu: QC duzeltme
yardimcisi llm.qc_fix ile; descriptor uretimi model ciktisini dogrulayicidan gecene kadar geri besler,
kabul edilen adayi KAYDETMEZ. Sahte istemci ile ag yok.
"""
import os
import unittest

from fastapi import HTTPException

from orchestrator import generation_mode as gm
from orchestrator.descriptor_example import EXAMPLE_USER_DESCRIPTOR
from orchestrator.llm import descriptor_gen
from orchestrator.llm.client import LlmConfig, env_secret


class _FakeClient:
    """Sirayla verilen cevaplari doner; gelen mesajlari kaydeder (geri besleme kontrolu icin)."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.calls: list[list[dict]] = []

    def chat(self, messages, *, temperature=0.2, max_tokens=None):
        self.calls.append(messages)
        return self.answers.pop(0)


class GenerationModeTests(unittest.TestCase):
    def test_default_is_static_and_llm_never_active(self) -> None:
        self.assertEqual(gm.generation_mode({"project": {}}), "static")
        self.assertFalse(gm.llm_active({"project": {"generation_mode": "static"}, "llm": {"enabled": True}}))
        self.assertFalse(gm.qc_fixer_active({"project": {"generation_mode": "static"}, "llm": {"enabled": True}}))

    def test_legacy_spec_without_mode_follows_llm_enabled(self) -> None:
        self.assertEqual(gm.generation_mode({"project": {}, "llm": {"enabled": True}}), "ai")
        self.assertTrue(gm.llm_active({"project": {}, "llm": {"enabled": True}}))

    def test_ai_mode_qc_fix_can_be_switched_off(self) -> None:
        spec = {"project": {"generation_mode": "ai"}, "llm": {"enabled": True, "qc_fix": False}}
        self.assertTrue(gm.llm_active(spec))
        self.assertFalse(gm.qc_fixer_active(spec))
        spec["llm"]["qc_fix"] = True
        self.assertTrue(gm.qc_fixer_active(spec))

    def test_jobs_fixer_is_none_in_static_mode_even_with_llm_enabled(self) -> None:
        from backend import jobs

        spec = {"project": {"generation_mode": "static"}, "llm": {"enabled": True, "base_url": "http://x/v1", "model": "m"}}
        self.assertIsNone(jobs._maybe_llm_fixer(spec, {}))

    def test_api_key_env_names_the_variable_not_the_secret(self) -> None:
        os.environ["SPEC2CODE_TEST_KEY_VAR"] = "gizli-anahtar"
        try:
            cfg = LlmConfig.resolve({"base_url": "http://x/v1", "model": "m", "api_key_env": "SPEC2CODE_TEST_KEY_VAR"})
            self.assertEqual(cfg.api_key, "gizli-anahtar")
            cfg = LlmConfig.resolve({"base_url": "http://x/v1", "model": "m", "api_key": "dogrudan", "api_key_env": "SPEC2CODE_TEST_KEY_VAR"})
            self.assertEqual(cfg.api_key, "dogrudan")
        finally:
            os.environ.pop("SPEC2CODE_TEST_KEY_VAR", None)
        # Tanimsiz degisken: bos anahtar (hata degil); ad bos ise hic aranmaz.
        self.assertEqual(env_secret("SPEC2CODE_TEST_KEY_VAR_YOK"), "")
        self.assertEqual(env_secret(""), "")


class DescriptorGenerationTests(unittest.TestCase):
    def test_catalog_operation_names_feed_the_prompt(self) -> None:
        names = descriptor_gen.catalog_operation_names()
        for op in ("device_init", "id_read", "x_read", "temperature_read"):
            self.assertIn(op, names)
        self.assertIn("x_read, y_read, z_read", descriptor_gen.system_prompt(names))

    def test_validator_errors_are_fed_back_and_valid_round_is_accepted(self) -> None:
        broken = EXAMPLE_USER_DESCRIPTOR.replace("op: poll", "op: pool")
        client = _FakeClient(["```yaml\n" + broken + "```", EXAMPLE_USER_DESCRIPTOR])
        result = descriptor_gen.generate_descriptor({}, "MYMON16", "REG 0x00 ...", rounds=3, client=client)
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["rounds"]), 2)
        self.assertTrue(result["rounds"][0]["errors"])
        self.assertEqual(result["rounds"][1]["errors"], [])
        self.assertEqual(result["yaml"].strip(), EXAMPLE_USER_DESCRIPTOR.strip())
        second_prompt = client.calls[1][1]["content"]
        self.assertIn("rejected by the validator", second_prompt)
        self.assertIn(result["rounds"][0]["errors"][0], second_prompt)
        self.assertIn("Previous YAML:", second_prompt)

    def test_part_mismatch_is_rejected_and_rounds_exhaust(self) -> None:
        client = _FakeClient([EXAMPLE_USER_DESCRIPTOR, EXAMPLE_USER_DESCRIPTOR])
        result = descriptor_gen.generate_descriptor({}, "OTHERPART", "ref", rounds=2, client=client)
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["rounds"]), 2)
        self.assertIn("uyusmuyor", result["rounds"][0]["errors"][0])

    def test_empty_reference_is_refused_before_any_llm_call(self) -> None:
        client = _FakeClient([])
        with self.assertRaises(ValueError):
            descriptor_gen.generate_descriptor({}, "X", "   ", client=client)
        self.assertEqual(client.calls, [])

    def test_endpoint_requires_ai_mode_llm_enabled(self) -> None:
        from backend.api import routes

        with self.assertRaises(HTTPException) as ctx:
            routes.llm_descriptor(routes.LlmDescriptorRequest(part="X", reference="ref", llm={"enabled": False}))
        self.assertEqual(ctx.exception.status_code, 400)
        with self.assertRaises(HTTPException) as ctx:
            routes.llm_descriptor(routes.LlmDescriptorRequest(part="X", reference="ref", llm={"enabled": True}))
        self.assertIn("llm invalid", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
