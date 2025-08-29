import json
from channels.generic.websocket import WebsocketConsumer
from celery.result import AsyncResult

class task_status_consumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        
    def disconnect(self, close_code):
        pass
    
    def receive(self, text_data):
        data = json.loads(text_data)
        task_id = data.get("task_id")
        
        #get celery tast result
        result = AsyncResult(task_id)
        response_data= {
            "task_id": task_id,
            "status": result.status,
        }
        
        if result.status == "PROGRESS":
            progress = result.result or {}
            response_data["progress"] = progress.get("percent", 0)
            
        elif result.status == "SUCCESS":
            response_data.update(result.result or {})
        
        elif result.status == "FAILURE":
            response_data["error"] = str(result.result)
            
        self.send(text_data=json.dumps(response_data))    