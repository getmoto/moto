class EC2Service:
    def __init__(self, plugin_directory):
        self.plugins = load_plugins(plugin_directory)

    def create_instance(self, request):
        # Call plugin hooks before processing
        for plugin in self.plugins:
            if hasattr(plugin, 'before_ec2_response'):
                plugin.before_ec2_response(request)

        # Actual EC2 instance creation logic here
        response = self.process_instance_creation(request)

        return response
