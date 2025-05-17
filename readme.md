### Prerequisites

- Downloaded trained model
- AWS IAM user with access to S3
- AWS IAM user with access to ELB
- AWS IAM user with access to SageMaker
- AWS CLI installed and configured

### Build & Run Commands

1. Upload the model to S3

    1. Be sure to have a standard model directory structure:

       ```
       saved_model_dir/
         ├── saved_model.pb
         └── variables/
       ```

    2. Zip it as **tar.gz** and upload the model to S3 using the AWS CLI:

       ```bash
       aws s3 cp --recursive "\path\to\your\saved_model" s3://your-bucket-name/tf1-model/
 
       ```

    3. Check the upload (optional):

       ```bash
       aws s3 ls s3://your-bucket-name/tf1-model/
       ```

2. Create IAM Role for SageMaker

    1. Create a `trust-policy.json` file with the following content:

       ```json
       {
         "Version": "2012-10-17",
         "Statement": [
           {
             "Effect": "Allow",
             "Principal": {
               "Service": "sagemaker.amazonaws.com"
             },
             "Action": "sts:AssumeRole"
           }
         ]
       }
       ```

    2. Create the IAM role using the AWS CLI:

       ```bash
       aws iam create-role --role-name AmazonSageMakerExecutionRole --assume-role-policy-document file://trust-policy.json
       ```

    3. Attach the necessary policies to the role:

       ```bash
       aws iam attach-role-policy --role-name AmazonSageMakerExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonS3FullAccess
       ```

    4. Get Role ARN:

       ```bash
       aws iam get-role --role-name AmazonSageMakerExecutionRole --query Role.Arn --output text
       ```

       The output will look like this:

       ```
       arn:aws:iam::************:role/AmazonSageMakerExecutionRole
       ```

    5. Copy the ARN and save it for later use.<br><br>

3. Deploy the model to SageMaker

    1. Create Model
       ```bash
       aws sagemaker create-model --model-name emotion-predict-model --primary-container Image=763104351884.dkr.ecr.ap-southeast-1.amazonaws.com/tensorflow-inference:1.15-cpu,ModelDataUrl=s3://your-bucket-name/tf1-model/model.tar.gz --execution-role-arn arn:aws:iam::************:role/AmazonSageMakerExecutionRole
       ```
    2. Create Endpoint Config
       ```bash
       aws sagemaker create-endpoint-config --endpoint-config-name emotion-predict-endpoint-config --production-variants VariantName=AllTraffic,ModelName=emotion-predict-model,InitialInstanceCount=1,InstanceType=ml.t2.medium, InitialVariantWeight=1.0
       ```
    3. Create Endpoint
       ```bash
       aws sagemaker create-endpoint --endpoint-name emotion-predict-endpoint --endpoint-config-name emotion-predict-endpoint-config
       ```
    4. Check Endpoint Status
       ```bash
       aws sagemaker describe-endpoint --endpoint-name emotion-predict-endpoint
       ```
       Wait until the status is `InService`. This may take a few minutes.<br><br>
    5. Your endpoint URL will be in the following format:
       ```
       https://runtime.sagemaker-ap-southeast-1.amazonaws.com/endpoints/emotion-predict-endpoint/invocations
       ```
       Now you have a SageMaker endpoint ready to receive `tf.train.Example` requests.  
       Next we'll be deploying a Flask app to AWS Elastic Beanstalk to serve the model.<br><br>

4. Package the Flask app

    1. Make sure you have this directory structure:
       ```
       SageFlask/
       ├── application.py
       ├── utils.py
       ├── bert/
       ├── static/
       ├── templates/
       ├── Dockerfile
       └── requirements.txt
       ```
    2. Zip the directory:
       ```bash
       cd SageFlask
       zip -r ../SageFlask.zip *
       ```
    3. Upload the zip file to S3:
       ```bash
       aws s3 cp ../SageFlask.zip s3://your-bucket-name/
       ```
    4. Check the upload (optional):
       ```bash
       aws s3 ls s3://your-bucket-name/
       ```

5. Create IAM user for Elastic Beanstalk

    1. Create `trust-policy.json` file with the following content:

       ```json
       {
         "Version": "2012-10-17",
         "Statement": [
           {
             "Effect": "Allow",
             "Principal": {
               "Service": "ec2.amazonaws.com"
             },
             "Action": "sts:AssumeRole"
           }
         ]
       }
       ```

    2. Create the IAM role using the AWS CLI:

       ```bash
       aws iam create-role --role-name EB-EC2-Role --assume-role-policy-document file://trust-policy.json
       ```

    3. Attach the necessary policies to the role:

       ```bash
       aws iam attach-role-policy --role-name EB-EC2-Role --policy-arn arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkWebTier
       aws iam attach-role-policy --role-name EB-EC2-Role --policy-arn arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkWorkerTier
       aws iam attach-role-policy --role-name EB-EC2-Role --policy-arn arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkMulticontainerDocker
       ```

    4. Create an instance profile for the role:

       ```bash
       aws iam create-instance-profile --instance-profile-name EB-EC2-Role-Profile
       aws iam add-role-to-instance-profile --instance-profile-name EB-EC2-Role-Profile --role-name EB-EC2-Role
       ```

    5. Create a `invoke-policy.json` file with the following content:

       ```json
       {
         "Version": "2012-10-17",
         "Statement": [
           {
             "Effect": "Allow",
             "Action": ["sagemaker:InvokeEndpoint"],
             "Resource": "arn:aws:sagemaker:ap-southeast-1:************:endpoint/emotion-predict-endpoint"
           }
         ]
       }
       ```

       Then run

       ```bash
       aws iam put-role-policy --role-name EB-EC2-Role --policy-name InvokeSageMakerEndpointPolicy --policy-document file://invoke-policy.json
       ```

6. Create a new Elastic Beanstalk application:

    1. Create a new application using the AWS CLI:
       ```bash
       aws elasticbeanstalk create-application --application-name emotion-predict-app --description "Emotion prediction Flask app (Docker)"
       ```
    2. Register a new application version:
       ```bash
       aws elasticbeanstalk create-application-version --application-name emotion-predict-app --version-label v1 --source-bundle S3Bucket=your-bucket-name,S3Key=SageFlask.zip
       ```
    3. Look for available platforms:
       ```bash
       aws elasticbeanstalk list-available-solution-stacks | findstr /C:"Docker"
       ```
       Choose a proper platform from the list. For example, `64bit Amazon Linux 2 v4.1.0 running Docker`<br><br>
    4. Create a new environment:
       ```bash
       aws elasticbeanstalk create-environment --application-name emotion-predict-app --environment-name emotion-predict-env --solution-stack-name "64bit Amazon Linux 2 v4.1.0 running Docker" --version-label v1 --option-settings Name=aws:elasticbeanstalk:environment:EnvironmentType,Value=LoadBalanced Name=aws:elasticbeanstalk:environment:EnvironmentName,Value=emotion-predict-env Name=aws:autoscaling:launchconfiguration:IamInstanceProfile,Value=EB-EC2-Role-Profile Namespace=aws:autoscaling:launchconfiguration,OptionName=IamInstanceProfile,Value=EB-EC2-Role-Profile
       ```
    5. Check the status of the environment:
       ```bash
       aws elasticbeanstalk describe-environments --application-name emotion-predict-app --environment-names emotion-predict-env --query "Environments[0].EndpointURL" --output text
       ```
       Wait until the response is like `emotion-predict-env.************.elasticbeanstalk.com`.  
       This may take a few minutes.<br><br>

7. Now you have a Flask app running on AWS Elastic Beanstalk that can serve the model deployed on SageMaker.
   <br><br>
   You can test this url by sending a POST request with a JSON payload (e.g.
   `{"text":"I enjoyed the movie. The CGI was AMAZING! Loved it."}`) to the endpoint URL.  
   A sample response will look like this:`{ "anger":0.847950339,"annoyance":0.49445802}`

### Directory Structure
Following the previous steps, you should have deployed the model to AWS SageMaker and the Flask app to AWS Elastic Beanstalk.  
No need for local directories.

### Contact
e1285202@u.nus.edu