"""Handles incoming servicecatalog requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse, TYPE_RESPONSE
from .models import servicecatalog_backends


class ServiceCatalogResponse(BaseResponse):
    """Handler for ServiceCatalog requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="servicecatalog")

    @property
    def servicecatalog_backend(self):
        """Return backend instance specific for this region."""
        return servicecatalog_backends[self.current_account][self.region]

    # add methods from here

    def create_portfolio(self):
        accept_language = self._get_param("AcceptLanguage")
        display_name = self._get_param("DisplayName")
        description = self._get_param("Description")
        provider_name = self._get_param("ProviderName")
        tags = self._get_param("Tags")
        idempotency_token = self._get_param("IdempotencyToken")

        portfolio_detail, tags = self.servicecatalog_backend.create_portfolio(
            accept_language=accept_language,
            display_name=display_name,
            description=description,
            provider_name=provider_name,
            tags=tags,
            idempotency_token=idempotency_token,
        )
        # TODO: adjust response
        return json.dumps(dict(PortfolioDetail=portfolio_detail.to_json(), Tags=tags))

    def list_portfolios(self) -> str:
        accept_language = self._get_param("AcceptLanguage")
        page_token = self._get_param("PageToken")
        page_size = self._get_param("PageSize")
        (portfolios, next_page_token,) = self.servicecatalog_backend.list_portfolios(
            accept_language=accept_language,
            page_token=page_token,
        )

        portfolio_details = [portfolio.to_json() for portfolio in portfolios]

        # TODO: adjust response

        ret = json.dumps(
            dict(
                PortfolioDetails=portfolio_details,
                NextPageToken=next_page_token,
            )
        )

        return ret

    def describe_provisioned_product(self):
        accept_language = self._get_param("AcceptLanguage")
        id = self._get_param("Id")
        name = self._get_param("Name")
        (
            provisioned_product_detail,
            cloud_watch_dashboards,
        ) = self.servicecatalog_backend.describe_provisioned_product(
            accept_language=accept_language,
            id=id,
            name=name,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ProvisionedProductDetail=provisioned_product_detail,
                CloudWatchDashboards=cloud_watch_dashboards,
            )
        )

    # add templates from here

    def get_provisioned_product_outputs(self):
        accept_language = self._get_param("AcceptLanguage")
        provisioned_product_id = self._get_param("ProvisionedProductId")
        provisioned_product_name = self._get_param("ProvisionedProductName")
        output_keys = self._get_param("OutputKeys")
        page_size = self._get_param("PageSize")
        page_token = self._get_param("PageToken")
        (
            outputs,
            next_page_token,
        ) = self.servicecatalog_backend.get_provisioned_product_outputs(
            accept_language=accept_language,
            provisioned_product_id=provisioned_product_id,
            provisioned_product_name=provisioned_product_name,
            output_keys=output_keys,
            page_token=page_token,
        )
        # TODO: adjust response
        return json.dumps(dict(Outputs=outputs, NextPageToken=next_page_token))

    def search_provisioned_products(self):
        accept_language = self._get_param("AcceptLanguage")
        access_level_filter = self._get_param("AccessLevelFilter")
        filters = self._get_param("Filters")
        sort_by = self._get_param("SortBy")
        sort_order = self._get_param("SortOrder")
        page_size = self._get_param("PageSize")
        page_token = self._get_param("PageToken")
        (
            provisioned_products,
            total_results_count,
            next_page_token,
        ) = self.servicecatalog_backend.search_provisioned_products(
            accept_language=accept_language,
            access_level_filter=access_level_filter,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page_token=page_token,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ProvisionedProducts=provisioned_products,
                TotalResultsCount=total_results_count,
                NextPageToken=next_page_token,
            )
        )

    def terminate_provisioned_product(self):
        provisioned_product_name = self._get_param("ProvisionedProductName")
        provisioned_product_id = self._get_param("ProvisionedProductId")
        terminate_token = self._get_param("TerminateToken")
        ignore_errors = self._get_param("IgnoreErrors")
        accept_language = self._get_param("AcceptLanguage")
        retain_physical_resources = self._get_param("RetainPhysicalResources")
        record_detail = self.servicecatalog_backend.terminate_provisioned_product(
            provisioned_product_name=provisioned_product_name,
            provisioned_product_id=provisioned_product_id,
            terminate_token=terminate_token,
            ignore_errors=ignore_errors,
            accept_language=accept_language,
            retain_physical_resources=retain_physical_resources,
        )
        # TODO: adjust response
        return json.dumps(dict(RecordDetail=record_detail))

    def search_products(self):
        accept_language = self._get_param("AcceptLanguage")
        filters = self._get_param("Filters")
        page_size = self._get_param("PageSize")
        sort_by = self._get_param("SortBy")
        sort_order = self._get_param("SortOrder")
        page_token = self._get_param("PageToken")
        (
            product_view_summaries,
            product_view_aggregations,
            next_page_token,
        ) = self.servicecatalog_backend.search_products(
            accept_language=accept_language,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page_token=page_token,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ProductViewSummaries=product_view_summaries,
                ProductViewAggregations=product_view_aggregations,
                NextPageToken=next_page_token,
            )
        )

    def list_launch_paths(self):
        accept_language = self._get_param("AcceptLanguage")
        product_id = self._get_param("ProductId")
        page_size = self._get_param("PageSize")
        page_token = self._get_param("PageToken")
        (
            launch_path_summaries,
            next_page_token,
        ) = self.servicecatalog_backend.list_launch_paths(
            accept_language=accept_language,
            product_id=product_id,
            page_token=page_token,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                LaunchPathSummaries=launch_path_summaries, NextPageToken=next_page_token
            )
        )

    def list_provisioning_artifacts(self):
        accept_language = self._get_param("AcceptLanguage")
        product_id = self._get_param("ProductId")
        (
            provisioning_artifact_details,
            next_page_token,
        ) = self.servicecatalog_backend.list_provisioning_artifacts(
            accept_language=accept_language,
            product_id=product_id,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ProvisioningArtifactDetails=provisioning_artifact_details,
                NextPageToken=next_page_token,
            )
        )

    def provision_product(self):
        accept_language = self._get_param("AcceptLanguage")
        product_id = self._get_param("ProductId")
        product_name = self._get_param("ProductName")
        provisioning_artifact_id = self._get_param("ProvisioningArtifactId")
        provisioning_artifact_name = self._get_param("ProvisioningArtifactName")
        path_id = self._get_param("PathId")
        path_name = self._get_param("PathName")
        provisioned_product_name = self._get_param("ProvisionedProductName")
        provisioning_parameters = self._get_param("ProvisioningParameters")
        provisioning_preferences = self._get_param("ProvisioningPreferences")
        tags = self._get_param("Tags")
        notification_arns = self._get_param("NotificationArns")
        provision_token = self._get_param("ProvisionToken")
        record_detail = self.servicecatalog_backend.provision_product(
            accept_language=accept_language,
            product_id=product_id,
            product_name=product_name,
            provisioning_artifact_id=provisioning_artifact_id,
            provisioning_artifact_name=provisioning_artifact_name,
            path_id=path_id,
            path_name=path_name,
            provisioned_product_name=provisioned_product_name,
            provisioning_parameters=provisioning_parameters,
            provisioning_preferences=provisioning_preferences,
            tags=tags,
            notification_arns=notification_arns,
            provision_token=provision_token,
        )
        # TODO: adjust response
        return json.dumps(dict(RecordDetail=record_detail))

    def create_product(self):
        accept_language = self._get_param("AcceptLanguage")
        name = self._get_param("Name")
        owner = self._get_param("Owner")
        description = self._get_param("Description")
        distributor = self._get_param("Distributor")
        support_description = self._get_param("SupportDescription")
        support_email = self._get_param("SupportEmail")
        support_url = self._get_param("SupportUrl")
        product_type = self._get_param("ProductType")
        tags = self._get_param("Tags")
        provisioning_artifact_parameters = self._get_param(
            "ProvisioningArtifactParameters"
        )
        idempotency_token = self._get_param("IdempotencyToken")
        source_connection = self._get_param("SourceConnection")
        (
            product_view_detail,
            provisioning_artifact_detail,
            tags,
        ) = self.servicecatalog_backend.create_product(
            accept_language=accept_language,
            name=name,
            owner=owner,
            description=description,
            distributor=distributor,
            support_description=support_description,
            support_email=support_email,
            support_url=support_url,
            product_type=product_type,
            tags=tags,
            provisioning_artifact_parameters=provisioning_artifact_parameters,
            idempotency_token=idempotency_token,
            source_connection=source_connection,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ProductViewDetail=product_view_detail,
                ProvisioningArtifactDetail=provisioning_artifact_detail,
                Tags=tags,
            )
        )

    def associate_product_with_portfolio(self):

        accept_language = self._get_param("AcceptLanguage")
        product_id = self._get_param("ProductId")
        portfolio_id = self._get_param("PortfolioId")
        source_portfolio_id = self._get_param("SourcePortfolioId")
        self.servicecatalog_backend.associate_product_with_portfolio(
            accept_language=accept_language,
            product_id=product_id,
            portfolio_id=portfolio_id,
            source_portfolio_id=source_portfolio_id,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def create_constraint(self):
        accept_language = self._get_param("AcceptLanguage")
        portfolio_id = self._get_param("PortfolioId")
        product_id = self._get_param("ProductId")
        parameters = self._get_param("Parameters")
        constraint_type = self._get_param("Type")
        description = self._get_param("Description")
        idempotency_token = self._get_param("IdempotencyToken")
        (
            constraint_detail,
            constraint_parameters,
            status,
        ) = self.servicecatalog_backend.create_constraint(
            accept_language=accept_language,
            portfolio_id=portfolio_id,
            product_id=product_id,
            parameters=parameters,
            constraint_type=constraint_type,
            description=description,
            idempotency_token=idempotency_token,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ConstraintDetail=constraint_detail,
                ConstraintParameters=constraint_parameters,
                Status=status,
            )
        )

    def describe_portfolio(self):
        accept_language = self._get_param("AcceptLanguage")
        identifier = self._get_param("Id")
        (
            portfolio_detail,
            tags,
            tag_options,
            budgets,
        ) = self.servicecatalog_backend.describe_portfolio(
            accept_language=accept_language,
            identifier=identifier,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                PortfolioDetail=portfolio_detail,
                Tags=tags,
                TagOptions=tag_options,
                Budgets=budgets,
            )
        )

    def describe_product_as_admin(self):
        accept_language = self._get_param("AcceptLanguage")
        identifier = self._get_param("Id")
        name = self._get_param("Name")
        source_portfolio_id = self._get_param("SourcePortfolioId")
        (
            product_view_detail,
            provisioning_artifact_summaries,
            tags,
            tag_options,
            budgets,
        ) = self.servicecatalog_backend.describe_product_as_admin(
            accept_language=accept_language,
            identifier=identifier,
            name=name,
            source_portfolio_id=source_portfolio_id,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ProductViewDetail=product_view_detail,
                ProvisioningArtifactSummaries=provisioning_artifact_summaries,
                Tags=tags,
                TagOptions=tag_options,
                Budgets=budgets,
            )
        )

    def describe_product(self):
        accept_language = self._get_param("AcceptLanguage")
        identifier = self._get_param("Id")
        name = self._get_param("Name")
        (
            product_view_summary,
            provisioning_artifacts,
            budgets,
            launch_paths,
        ) = self.servicecatalog_backend.describe_product(
            accept_language=accept_language,
            identifier=identifier,
            name=name,
        )
        # TODO: adjust response
        return json.dumps(
            dict(
                ProductViewSummary=product_view_summary,
                ProvisioningArtifacts=provisioning_artifacts,
                Budgets=budgets,
                LaunchPaths=launch_paths,
            )
        )

    def update_portfolio(self):
        accept_language = self._get_param("AcceptLanguage")
        identifier = self._get_param("Id")
        display_name = self._get_param("DisplayName")
        description = self._get_param("Description")
        provider_name = self._get_param("ProviderName")
        add_tags = self._get_param("AddTags")
        remove_tags = self._get_param("RemoveTags")
        portfolio_detail, tags = self.servicecatalog_backend.update_portfolio(
            accept_language=accept_language,
            identifier=identifier,
            display_name=display_name,
            description=description,
            provider_name=provider_name,
            add_tags=add_tags,
            remove_tags=remove_tags,
        )
        # TODO: adjust response
        return json.dumps(dict(PortfolioDetail=portfolio_detail, Tags=tags))

    def update_product(self):
        accept_language = self._get_param("AcceptLanguage")
        identifier = self._get_param("Id")
        name = self._get_param("Name")
        owner = self._get_param("Owner")
        description = self._get_param("Description")
        distributor = self._get_param("Distributor")
        support_description = self._get_param("SupportDescription")
        support_email = self._get_param("SupportEmail")
        support_url = self._get_param("SupportUrl")
        add_tags = self._get_param("AddTags")
        remove_tags = self._get_param("RemoveTags")
        source_connection = self._get_param("SourceConnection")
        product_view_detail, tags = self.servicecatalog_backend.update_product(
            accept_language=accept_language,
            identifier=identifier,
            name=name,
            owner=owner,
            description=description,
            distributor=distributor,
            support_description=support_description,
            support_email=support_email,
            support_url=support_url,
            add_tags=add_tags,
            remove_tags=remove_tags,
            source_connection=source_connection,
        )
        # TODO: adjust response
        return json.dumps(dict(ProductViewDetail=product_view_detail, Tags=tags))

    def list_portfolios_for_product(self):
        accept_language = self._get_param("AcceptLanguage")
        product_id = self._get_param("ProductId")
        page_token = self._get_param("PageToken")
        page_size = self._get_param("PageSize")
        (
            portfolio_details,
            next_page_token,
        ) = self.servicecatalog_backend.list_portfolios_for_product(
            accept_language=accept_language,
            product_id=product_id,
            page_token=page_token,
        )
        # TODO: adjust response
        return json.dumps(
            dict(PortfolioDetails=portfolio_details, NextPageToken=next_page_token)
        )
