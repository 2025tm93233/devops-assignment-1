pipeline {
    agent any

    environment {
        IMAGE_NAME = 'aceest-fitness'
    }

    stages {
        stage('Run unit tests') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m unittest discover -s . -p "test_*.py" -v'
                    } else {
                        bat 'py -3 -m unittest discover -s . -p "test_*.py" -v'
                    }
                }
            }
        }

        stage('Build Docker image') {
            steps {
                script {
                    if (isUnix()) {
                        sh "docker build --tag ${env.IMAGE_NAME}:${env.BUILD_NUMBER} --tag ${env.IMAGE_NAME}:latest ."
                    } else {
                        bat "docker build --tag ${env.IMAGE_NAME}:${env.BUILD_NUMBER} --tag ${env.IMAGE_NAME}:latest ."
                    }
                }
            }
        }
    }
}
