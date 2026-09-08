from PIL import Image


MODEL_NAME = "dima806/ai_vs_real_image_detection"
MODEL_ARCHITECTURE = "ViTForImageClassification"


class AIImageDetector:

    def __init__(self):

        import torch
        from transformers import (
            AutoImageProcessor,
            AutoModelForImageClassification
        )

        print("[AIMD] Loading AI image detector...")

        self._torch = torch
        self.device = self._get_device()

        print(f"[AIMD] Device: {self.device}")
        print(f"[AIMD] Model: {MODEL_NAME}")

        self.processor = AutoImageProcessor.from_pretrained(
            MODEL_NAME
        )

        self.model = AutoModelForImageClassification.from_pretrained(
            MODEL_NAME
        )

        self.model.to(self.device)
        self.model.eval()

        print("[AIMD] ML detector loaded successfully.")

    def _get_device(self):

        if self._torch.backends.mps.is_available():
            return self._torch.device("mps")

        if self._torch.cuda.is_available():
            return self._torch.device("cuda")

        return self._torch.device("cpu")

    def predict(self, image_path: str) -> dict:

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception:
            return {
                "status": "unavailable",
                "model": MODEL_NAME,
                "architecture": MODEL_ARCHITECTURE,
                "prediction": "INCONCLUSIVE",
                "confidence": 0.0,
                "ai_probability": None,
                "human_probability": None,
                "raw_scores": {},
                "reason": "The image could not be opened for ML inference.",
            }

        try:
            inputs = self.processor(
                images=image,
                return_tensors="pt"
            )

            inputs = {
                key: value.to(self.device)
                for key, value in inputs.items()
            }

            with self._torch.no_grad():

                outputs = self.model(**inputs)

                probabilities = self._torch.softmax(
                    outputs.logits,
                    dim=-1
                )[0]
        except Exception:
            return {
                "status": "unavailable",
                "model": MODEL_NAME,
                "architecture": MODEL_ARCHITECTURE,
                "prediction": "INCONCLUSIVE",
                "confidence": 0.0,
                "ai_probability": None,
                "human_probability": None,
                "raw_scores": {},
                "reason": "ML inference failed.",
            }

        scores = {}

        for index, probability in enumerate(probabilities):

            label = self.model.config.id2label[index]

            scores[label] = float(probability.item())

        ai_score = 0.0
        human_score = 0.0

        for label, score in scores.items():

            normalized_label = label.lower()

            if any(marker in normalized_label for marker in ("ai", "fake", "synthetic", "artificial")):

                ai_score = score

            elif any(marker in normalized_label for marker in ("human", "real", "authentic")):

                human_score = score

        if not scores:
            return {
                "status": "unavailable",
                "model": MODEL_NAME,
                "architecture": MODEL_ARCHITECTURE,
                "prediction": "INCONCLUSIVE",
                "confidence": 0.0,
                "ai_probability": None,
                "human_probability": None,
                "raw_scores": {},
                "reason": "The ML detector returned an unusable output.",
            }

        if ai_score >= human_score:

            prediction = "AI-GENERATED"
            confidence = ai_score

        else:

            prediction = "HUMAN"
            confidence = human_score

        return {
            "status": "available",
            "model": MODEL_NAME,
            "architecture": MODEL_ARCHITECTURE,
            "prediction": prediction,
            "confidence": round(confidence, 6),
            "ai_probability": round(ai_score, 6),
            "human_probability": round(human_score, 6),
            "raw_scores": scores
        }


class UnavailableAIImageDetector:

    def __init__(self, reason: str = "PyTorch or Transformers is not installed."):
        self.reason = reason

    def predict(self, image_path: str) -> dict:
        return {
            "status": "unavailable",
            "model": MODEL_NAME,
            "architecture": MODEL_ARCHITECTURE,
            "prediction": "INCONCLUSIVE",
            "confidence": 0.0,
            "ai_probability": None,
            "human_probability": None,
            "raw_scores": {},
            "reason": self.reason,
        }


_detector = None


def get_detector():

    global _detector

    if _detector is None:
        try:
            _detector = AIImageDetector()
        except ImportError:
            _detector = UnavailableAIImageDetector(
                "PyTorch or Transformers is not installed."
            )
        except Exception:
            return UnavailableAIImageDetector(
                "The open-weight classifier could not be loaded."
            )

    return _detector
