pipeline {
    agent any

    triggers {
        upstream(upstreamProjects: "IMIO-github-Jenkinsfile/imio.pm.ws/master", threshold: hudson.model.Result.SUCCESS)
    }

    options {
        disableConcurrentBuilds()
        parallelsAlwaysFailFast()
    }

    environment{
        ZSERVER_PORT="32555"
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
            }
        }

        stage('Unit Test') {
            steps {
                sh "bin/python bin/test"
            }

        }
        stage('Code Analysis') {
            steps {
                sh "bin/python bin/code-analysis"
                warnings canComputeNew: false, canResolveRelativePaths: false, parserConfigurations: [[parserName: 'Pep8', pattern: '**/parts/code-analysis/flake8.log']]
            }
        }
        stage('Test Coverage') {
            steps {
                sh "bin/python bin/coverage run --source=imio.pm.wsclient bin/test"
                sh 'bin/python bin/coverage xml -i'
                cobertura coberturaReportFile: '**/coverage.xml', conditionalCoverageTargets: '70, 50, 20', lineCoverageTargets: '80, 50, 20', maxNumberOfBuilds: 0, methodCoverageTargets: '80, 50, 20', onlyStable: false, sourceEncoding: 'ASCII'
            }
        }
    }
    post{
        always{
            	hangoutsNotify message: "Lorem Ipsum is simply dummy text",
                    threadByJob: false

                hangoutsNotifySuccess threadByJob: false

                hangoutsNotifyFailure threadByJob: true

                hangoutsNotifyBuildStart threadByJob: true

                hangoutsNotifyBackToNormal threadByJob: true

                hangoutsNotifyAborted threadByJob: true

                hangoutsNotifyNotBuilt threadByJob: true

                hangoutsNotifyUnstable threadByJob: true
        }
        cleanup{
             deleteDir()
        }
    }
}
