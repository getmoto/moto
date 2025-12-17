import { CreateBucketCommand, S3Client } from '@aws-sdk/client-s3'

process.env['AWS_ACCESS_KEY_ID'] = 'test'
process.env['AWS_SECRET_ACCESS_KEY'] = 'test'


const s3 = new S3Client({
  region:'us-east-1',
  endpoint: 'http://localhost:5000',
  forcePathStyle: true,
})

s3.send(new CreateBucketCommand({ Bucket: 'asdfqwerasdfqwe3' }))
