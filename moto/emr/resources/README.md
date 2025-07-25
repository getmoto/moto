## Purpose 
Folder containing data about all resource types

## Layout
There are three resources in here:
 - Release labels per region (`release-labels-{region}.json`)
 - Instance type names per release label (`instance-types-{release_label}.json`)
 - Instance type details (all in `instance_types.json`)

AWS returns all instance type details when calling `list_supported_instance_types(ReleaseLabel=release_label)`.
However, because a large number of instance types are shared across all regions/release labels, and they all have the same details, we only store the details once to store space.

The naive way, to store all details per release label, would result in 11MB of JSON-files. The current solution only takes up 1.2MB.

## Automation
There is a script that automatically pulls this data from AWS:

```bash
python scripts/emr_get_releases.py
```
