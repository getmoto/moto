var AWS = require('aws-sdk');

var s3 = new AWS.S3({endpoint: "http://localhost:5000"});
var myBucket = 'my.unique.bucket.name';

var myKey = 'myBucketKey';

s3.createBucket({Bucket: myBucket}, function(err, data) {
    if (err) {
       console.log(err);
       } else {
         params = {Bucket: myBucket, Key: myKey, Body: 'Hello!'};
         s3.putObject(params, function(err, data) {
             if (err) {
                 console.log(err)
             } else {
                 console.log("Successfully uploaded data to myBucket/myKey");
             }
          });
       }
});

s3.listBuckets(function(err, data) {
  if (err) console.log(err, err.stack); // an error occurred
  else     console.log(data);           // successful response
});
