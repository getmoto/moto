from moto.core.responses import BaseResponse


class RouteTables(BaseResponse):
    def associate_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).associate_route_table is not yet implemented')

    def create_route(self):
        raise NotImplementedError('RouteTables(AmazonVPC).create_route is not yet implemented')

    def create_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).create_route_table is not yet implemented')

    def delete_route(self):
        raise NotImplementedError('RouteTables(AmazonVPC).delete_route is not yet implemented')

    def delete_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).delete_route_table is not yet implemented')

    def describe_route_tables(self):
        raise NotImplementedError('RouteTables(AmazonVPC).describe_route_tables is not yet implemented')

    def disassociate_route_table(self):
        raise NotImplementedError('RouteTables(AmazonVPC).disassociate_route_table is not yet implemented')

    def replace_route(self):
        raise NotImplementedError('RouteTables(AmazonVPC).replace_route is not yet implemented')

    def replace_route_table_association(self):
        raise NotImplementedError('RouteTables(AmazonVPC).replace_route_table_association is not yet implemented')
