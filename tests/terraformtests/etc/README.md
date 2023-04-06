### What is the purpose of this folder?

This folder contains git-patches for the Terraform repository. When running Terraform-tests against Moto, these patches will be applied automatically.

See http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html#terraform-tests on how to run the tests.

#### What kind of patches are there?
 - Patches that set the endpoint to localhost, to ensure the tests are run against Moto
 - Patches that reduce the wait time for resources. AWS may take a few minutes before an EC2 instance is spun up, Moto does this immediately - so it's not necessary for Terraform to wait until resources are ready
 - etc

#### How do I create a new patch?

 - Checkout the repository, and open a terminal in the root-directory
 - Go into the Terraform-directory:
   ```commandline
   cd tests/terraformtests/terraform-provider-aws
   ```
 - Ensure the right Terraform-branch is selected, and is clean:
   ```commandline
   git checkout main
   git checkout .
   ```
 - Create a new branch:
   ```commandline
   git checkout -b patch-my-changes
   ```
 - Make the required changes.
 - Commit your changes
 - Create a patch:
   ```commandline
    git format-patch main
   ```
 - Move the created patch-file into this folder
 - Update `tests/terraformtests/bin/run_go_test` with the new patch-file

