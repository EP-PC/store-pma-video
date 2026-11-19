pipeline {
    agent any
    environment {
        SERVICE = 'order'
        NAME = "enzoperego/${env.SERVICE}"
    }
    stages {
        stage('Dependencies') {
            steps {
                // os dois contratos que o order-service compila: o proprio (store:order) e o do Product
                build job: 'order', wait: true
                build job: 'product', wait: true
            }
        }
        stage('Build') {
            steps {
                // Diferente do modelo: SEM -DskipTests. Os testes usam so mocks (sem banco nem rede),
                // entao rodam no Jenkins; um teste falhando para o pipeline antes de publicar a imagem.
                sh 'mvn -B clean package'
            }
            post {
                always {
                    // relatorio dos testes na pagina do build (plugin JUnit)
                    junit allowEmptyResults: true, testResults: 'target/surefire-reports/*.xml'
                }
            }
        }
        stage('Build & Push Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credential', usernameVariable: 'USERNAME', passwordVariable: 'TOKEN')]) {
                    sh 'echo $TOKEN | docker login -u $USERNAME --password-stdin'
                    sh "docker buildx create --use --platform=linux/arm64,linux/amd64 --node multi-platform-builder-${env.SERVICE} --name multi-platform-builder-${env.SERVICE}"
                    sh "docker buildx build --platform=linux/arm64,linux/amd64 --push --tag ${env.NAME}:latest --tag ${env.NAME}:${env.BUILD_ID} -f Dockerfile ."
                    sh "docker buildx rm --force multi-platform-builder-${env.SERVICE}"
                }
            }
        }
        stage('Deploy to EKS') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'aws-credential',
                        usernameVariable: 'AWS_ACCESS_KEY_ID', passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                    sh '''
                        export AWS_DEFAULT_REGION=us-east-2
                        trap 'rm -f ./kubeconfig' EXIT
                        if ! out=$(aws eks describe-cluster --name eks-store 2>&1); then
                            if echo "$out" | grep -q ResourceNotFoundException; then
                                echo "Cluster eks-store nao esta de pe: pulando o deploy"; exit 0
                            fi
                            echo "$out"; exit 1
                        fi
                        aws eks update-kubeconfig --name eks-store --kubeconfig ./kubeconfig
                        kubectl --kubeconfig ./kubeconfig set image deployment/${SERVICE} ${SERVICE}=${NAME}:${BUILD_ID}
                        kubectl --kubeconfig ./kubeconfig rollout status deployment/${SERVICE} --timeout=300s
                    '''
                }
            }
        }
    }
}
