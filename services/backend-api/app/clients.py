import httpx
from pydantic import ValidationError

from app.schemas import Prediction


class ModelUnavailable(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class ModelClient:
    def __init__(self, base_url: str, token: str, timeout: float):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._http = httpx.Client(base_url=base_url, headers=headers, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def predict(self, subject: str | None, body: str, request_id: str) -> Prediction:
        try:
            r = self._http.post(
                "/predict",
                json={"subject": subject, "body": body},
                headers={"X-Request-ID": request_id},
            )
            r.raise_for_status()
            return Prediction.model_validate(r.json())
        except httpx.TimeoutException:
            reason = "timeout"
        except httpx.HTTPError:
            reason = "http_error"
        except (ValueError, ValidationError):  # bad JSON or wrong shape
            reason = "bad_response"
        raise ModelUnavailable(reason)
