.. _prettify_responses_page:

.. role:: raw-html(raw)
    :format: html

=============================
Prettify responses
=============================

This option allows to prettify responses from moto. Pretty responses are more readable (eg. for debugging purposes). 
It also makes moto better in mocking AWS as AWS returns prettified responses.

Ugly output:

.. sourcecode:: python

    <DeleteLaunchTemplatesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/"><requestId>178936da-50ad-4d58-8871-22d9979e8658example</requestId><launchTemplate><defaultVersionNumber>1</defaultVersionNumber><launchTemplateId>lt-d920e32b0cccd6adb</launchTemplateId><launchTemplateName>example-name</launchTemplateName></launchTemplate></DeleteLaunchTemplatesResponse>

Prettified output:

.. sourcecode:: python

    <DeleteLaunchTemplatesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <requestId>178936da-50ad-4d58-8871-22d9979e8658example</requestId>
        <launchTemplate>
            <defaultVersionNumber>1</defaultVersionNumber>
            <launchTemplateId>lt-d920e32b0cccd6adb</launchTemplateId>
            <launchTemplateName>example-name</launchTemplateName>
        </launchTemplate>
    </DeleteLaunchTemplatesResponse>


Enabling Pretty responses
#########################

As changing responses can interfere with some external tools, it is disabled by default.
If you want to enable it, use environment variable:
`MOTO_PRETTIFY_RESPONSES=True`