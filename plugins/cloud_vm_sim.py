# plugins/cloud_vm_sim.py
class Plugin:
    def before_ec2_response(self, request):
        # Call your cloud-vm-sim service with userdata
        userdata = request.get('UserData')
        # Add logic to call your cloud-vm-sim service here
