from locust import HttpUser, task, between
import uuid
import random

class PaytmUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def transfer(self):
        # Simulate 1000s of users hitting the API
        self.client.post("/transfer", json={
            "sender_user_id": "user_A",
            "receiver_user_id": "user_B",
            "amount": 1.00,
            "reference_id": str(uuid.uuid4())
        })