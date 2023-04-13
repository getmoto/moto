# batch_simple

Batch jobs run under `batch_simple` will succeed by default. To make the jobs fail:

1. set environment variable `MOTO_SIMPLE_BATCH_FAIL_AFTER=0` OR 
2. set environment variable `MOTO_SIMPLE_BATCH_FAIL_AFTER` to an integer value 
   to make it fail after that number of seconds, ie `MOTO_SIMPLE_BATCH_FAIL_AFTER=4` will fail after 4 seconds
