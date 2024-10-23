from moto import mock_s3
import boto3

# Custom callback to log events
def custom_callback(event_type, bucket_name, object_key=None):
    """
    Custom callback function to handle S3 events such as bucket creation or object upload.
    """
    if event_type == "create_bucket":
        print(f"Bucket '{bucket_name}' has been created.")
    elif event_type == "upload_object":
        print(f"Object '{object_key}' has been uploaded to bucket '{bucket_name}'.")

# Wrapper to extend Moto functionality with callbacks
class MotoExtension:
    def __init__(self):
        self.callbacks = {}

    def register_callback(self, event_type, callback):
        """
        Register a callback for a specific event type.
        """
        self.callbacks[event_type] = callback

    def trigger_callback(self, event_type, bucket_name, object_key=None):
        """
        Trigger the registered callback for a specific event type.
        """
        if event_type in self.callbacks:
            self.callbacks[event_type](event_type, bucket_name, object_key)
        else:
            print(f"No callback registered for event '{event_type}'.")

# Example usage of Moto and custom callback
@mock_s3
def create_bucket_with_callback():
    # Initialize Moto S3 mock
    s3_client = boto3.client("s3", region_name="us-east-1")
    
    # Initialize the extension and register the callback
    extension = MotoExtension()
    extension.register_callback("create_bucket", custom_callback)
    extension.register_callback("upload_object", custom_callback)
    
    # Create a bucket and trigger the callback
    bucket_name = "my-test-bucket"
    s3_client.create_bucket(Bucket=bucket_name)
    extension.trigger_callback("create_bucket", bucket_name)
    
    # Upload an object and trigger the callback
    object_key = "my-file.txt"
    s3_client.put_object(Bucket=bucket_name, Key=object_key, Body="Hello Moto")
    extension.trigger_callback("upload_object", bucket_name, object_key)

if __name__ == "__main__":
    create_bucket_with_callback()
