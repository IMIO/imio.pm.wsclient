pipeline {
    agent any

    triggers {
        upstream(upstreamProjects: "IMIO-github-Jenkinsfile/imio.pm.ws/master", threshold: hudson.model.Result.SUCCESS)
    }

    options {
        disableConcurrentBuilds()
        parallelsAlwaysFailFast()
    }

    stages {
        stage('Build') {
            steps {
                cache(maxCacheSize: 850,
                      caches: [[$class: 'ArbitraryFileCache', excludes: '', path: "${WORKSPACE}/eggs"]]){

                    script {
                        sh "make bootstrap"
                        sh "bin/python bin/buildout -c jenkins.cfg"
                    }
                }
                stash 'workspace'
            }
        }

        stage('Run Tests') {
            parallel {
                stage('Unit Test') {
                    steps {
                        dir('unit_test') {
                            unstash 'workspace'
                            sh "bin/python bin/test"
                        }
                    }

                }
                stage('Code Analysis') {
                    steps {
                        dir('code_analysis') {
                            unstash 'workspace'
                            script {
                                sh "bin/python bin/code-analysis"
                                warnings canComputeNew: false, canResolveRelativePaths: false, parserConfigurations: [[parserName: 'Pep8', pattern: '**/parts/code-analysis/flake8.log']]
                            }
                        }
                    }
                }
                stage('Test Coverage') {
                    steps {
                        dir('test_coverage') {
                            unstash 'workspace'
                            script {
                                sh "bin/python bin/coverage run --source=imio.pm.wsclient bin/test"
                                sh 'bin/python bin/coverage xml -i'
                                cobertura coberturaReportFile: '**/coverage.xml', conditionalCoverageTargets: '70, 0, 0', lineCoverageTargets: '80, 0, 0', maxNumberOfBuilds: 0, methodCoverageTargets: '80, 0, 0', onlyStable: false, sourceEncoding: 'ASCII'
                            }
                        }
                    }
                }
            }
        }
    }
    post{
        always{
            chuckNorris()
        }
        aborted{
            mail to: 'pm-interne@imio.be',
                 subject: "Aborted Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline ${env.JOB_NAME} ${env.BUILD_NUMBER} was aborted (${env.BUILD_URL})"

            slackSend channel: "#jenkins",
                      color: "#C0C0C0",
                      message: "Aborted ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
        regression{
            mail to: 'pm-interne@imio.be',
                 subject: "Broken Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline ${env.JOB_NAME} ${env.BUILD_NUMBER} is broken (${env.BUILD_URL})"

            slackSend channel: "#jenkins",
                      color: "#ff0000",
                      message: "Broken ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
        fixed{
            mail to: 'pm-interne@imio.be',
                 subject: "Fixed Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline ${env.JOB_NAME} ${env.BUILD_NUMBER} is back to normal (${env.BUILD_URL})"

            slackSend channel: "#jenkins",
                      color: "#00cc44",
                      message: "Fixed ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
        failure{
            mail to: 'pm-interne@imio.be',
                 subject: "Failed Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline${env.JOB_NAME} ${env.BUILD_NUMBER} failed (${env.BUILD_URL})"

            slackSend channel: "#jenkins",
                      color: "#ff0000",
                      message: "Failed ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
        cleanup{
            deleteDir()
        }
    }
}
