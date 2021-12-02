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
        ZSERVER_PORT=String.valueOf(Math.abs( new Random().nextInt() % (65534 - 30000) ) + 30000)
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
            }
        }

        stage('Publish Coverage') {
            steps {
                catchError(buildResult: null, stageResult: 'FAILURE') {
                    cobertura (
                        coberturaReportFile: '**/coverage.xml',
                        conditionalCoverageTargets: '70, 50, 20',
                        lineCoverageTargets: '80, 50, 20',
                        maxNumberOfBuilds: 1,
                        methodCoverageTargets: '80, 50, 20',
                        onlyStable: false,
                        sourceEncoding: 'ASCII'
                    )
                }
            }
        }
    }
    post{
        aborted{
            mail to: 'pm-interne@imio.be',
                 subject: "Aborted Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline ${env.JOB_NAME} ${env.BUILD_NUMBER} was aborted (${env.BUILD_URL})"

            hangoutsNotifyAborted threadByJob: true
        }
        regression{
            mail to: 'pm-interne@imio.be',
                 subject: "Broken Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline ${env.JOB_NAME} ${env.BUILD_NUMBER} is broken (${env.BUILD_URL})"

            hangoutsNotifyUnstable threadByJob: true
        }
        fixed{
            mail to: 'pm-interne@imio.be',
                 subject: "Fixed Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline ${env.JOB_NAME} ${env.BUILD_NUMBER} is back to normal (${env.BUILD_URL})"

            hangoutsNotifyBackToNormal threadByJob: true
        }
        failure{
            mail to: 'pm-interne@imio.be',
                 subject: "Failed Pipeline: ${currentBuild.fullDisplayName}",
                 body: "The pipeline${env.JOB_NAME} ${env.BUILD_NUMBER} failed (${env.BUILD_URL})"

            hangoutsNotifyFailure threadByJob: true
        }
        cleanup{
             deleteDir()
        }
    }
}
