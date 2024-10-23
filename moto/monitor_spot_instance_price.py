import boto3
import time
from moto import mock_ec2

# Mock EC2 using Moto
@mock_ec2
def monitor_spot_instance_price():
    # Initialize a session with EC2
    ec2_client = boto3.client('ec2', region_name='us-east-1')

    # Create an instance (simulated)
    response = ec2_client.request_spot_instances(
        SpotPrice="0.03",  # Mocked price
        InstanceCount=1,
        LaunchSpecification={
            'ImageId': 'ami-0abcdef12345',  # Mocked AMI
            'InstanceType': 't2.micro'
        }
    )

    request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    print(f"Spot instance request created with ID: {request_id}")

    # Simulated price updates over time (since Moto doesn't do real-time pricing)
    spot_prices = [0.025, 0.035, 0.029, 0.045]  # Simulating some price fluctuations
    for idx, price in enumerate(spot_prices):
        print(f"Checking Spot price at time {idx}: ${price}")
        if price > 0.03:
            print(f"Spot price of ${price} exceeds the bid price of $0.03. Instance might be terminated.")
        else:
            print(f"Spot price of ${price} is within the bid price. Instance is running.")

        time.sleep(1)  # Simulate time passing

    print("Monitoring finished.")

if __name__ == "__main__":
    monitor_spot_instance_price()
