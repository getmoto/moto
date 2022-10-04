.. _mokey_patch_page:

.. role:: raw-html(raw)
    :format: html

=============================
Monkey Patch
=============================

The purpose of this monkey patch is to change behaviour of an external library for purposes of moto code.

Jinja Render
#################

Jinja render is returning responses in the form of unformattet single line xml string. 

.. sourcecode:: pytho

    <DeleteLaunchTemplatesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/"><requestId>178936da-50ad-4d58-8871-22d9979e8658example</requestId><launchTemplate><defaultVersionNumber>1</defaultVersionNumber><launchTemplateId>lt-d920e32b0cccd6adb</launchTemplateId><launchTemplateName>example-name</launchTemplateName></launchTemplate></DeleteLaunchTemplatesResponse>

This patch will cause returned responses to be formatted with newlines and indentations.

.. sourcecode:: python

    <DeleteLaunchTemplatesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <requestId>178936da-50ad-4d58-8871-22d9979e8658example</requestId>
        <launchTemplate>
            <defaultVersionNumber>1</defaultVersionNumber>
            <launchTemplateId>lt-d920e32b0cccd6adb</launchTemplateId>
            <launchTemplateName>example-name</launchTemplateName>
        </launchTemplate>
    </DeleteLaunchTemplatesResponse>

This change is introduced to make responses from moto more readable eg. for debugging purposes.

Configuration
#################

As changing responses can interfere with some external tools it is disabled by default.
If you want to enable it use enviroment variable:
`MOTO_PRETTIFY_RESPONSES=True`