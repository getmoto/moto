.. _state transition_models:

.. role:: raw-html(raw)
    :format: html

============================================
Supported Models for State Transitions
============================================


Service: Batch
-----------------

**Model**: `batch::job`  :raw-html:`<br />`
Available States:  :raw-html:`<br />`

    "SUBMITTED" --> "PENDING" --> "RUNNABLE" --> "STARTING" --> "RUNNING"  :raw-html:`<br />`
    "RUNNING" --> SUCCEEDED|FAILED

Transition type: `immediate`  :raw-html:`<br />`
Advancement:

    When a user calls `submit_job`, Moto will go through a few steps to prepare the job, and when ready, execute that job in a Docker container.
    There are some steps to go through while the status is `SUBMITTED`, there are some steps to follow when the status is `PENDING`, etcetera.

    Moto will try to advance the status itself - the moment this succeeds, the next step is executed.
    As the default transition is `immediate`, the status will advance immediately, and these steps will be executed as quickly as possible. This ensures that the job will be executed as quickly as possible.

    Delaying the execution can be done as usual, by forcing Moto to wait x seconds before transitioning to the next stage. This can be useful if you need to 'catch' a job in a specific stage.

Service: Cloudfront
---------------------

**Model**: `cloudfront::distribution`  :raw-html:`<br />`
Available States:  :raw-html:`<br />`

    "InProgress" --> "Deployed"

Transition type: Manual - describe the resource 1 time before the state advances  :raw-html:`<br />`
Advancement:

    Call `boto3.client("cloudfront").get_distribution(..)` to advance a single distribution, or  `boto3.client("cloudfront").list_distributions(..)` to advance all distributions.


Service: DAX
---------------

**Model**: `dax::cluster`   :raw-html:`<br />`
Available States:

    "creating" --> "available"   :raw-html:`<br />`
    "deleting" --> "deleted"

Transition type: Manual - describe the resource 4 times before the state advances   :raw-html:`<br />`
Advancement:

    Call `boto3.client("dax").describe_clusters(..)`.

Service: S3 (Glacier Restoration)
-----------------------------------

**Model**: `s3::keyrestore`   :raw-html:`<br />`
Available States:

    None --> "IN_PROGRESS" --> "RESTORED"

Transition type: Immediate - transitions immediately

Service: Support
------------------

**Model**: `support::case`   :raw-html:`<br />`
Available states:

    "opened" --> "pending-customer-action" --> "reopened" --> "resolved" --> "unassigned" --> "work-in-progress" --> "opened"

Transition type: Manual - describe the resource 1 time before the state advances    :raw-html:`<br />`
Advancement:

    Call `boto3.client("support").describe_cases(..)`

Service: Transcribe
---------------------

**Model**: `transcribe::vocabulary`   :raw-html:`<br />`
Available states:

    None --> "PENDING --> "READY"

Transition type: Manual - describe the resource 1 time before the state advances    :raw-html:`<br />`
Advancement:

    Call `boto3.client("transcribe").get_vocabulary(..)`

**Model**: `transcribe::medicalvocabulary`   :raw-html:`<br />`
Available states:

    None --> "PENDING --> "READY"

Transition type: Manual - describe the resource 1 time before the state advances    :raw-html:`<br />`
Advancement:

    Call `boto3.client("transcribe").get_medical_vocabulary(..)`

**Model**: `transcribe::transcriptionjob`   :raw-html:`<br />`
Available states:

    None --> "QUEUED" --> "IN_PROGRESS" --> "COMPLETED"

Transition type: Manual - describe the resource 1 time before the state advances    :raw-html:`<br />`
Advancement:

    Call `boto3.client("transcribe").get_transcription_job(..)`

**Model**: `transcribe::medicaltranscriptionjob`   :raw-html:`<br />`
Available states:

    None --> "QUEUED" --> "IN_PROGRESS" --> "COMPLETED"

Transition type: Manual - describe the resource 1 time before the state advances    :raw-html:`<br />`
Advancement:

    Call `boto3.client("transcribe").get_medical_transcription_job(..)`
