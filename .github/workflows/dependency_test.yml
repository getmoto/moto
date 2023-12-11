name: "Service-specific Dependencies Test"

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * *'  # every day at midnight

jobs:
  prepare_list:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - id: set-matrix
      run: echo "matrix=[$(ls -A1 moto | grep -v '.py' | awk '{ printf "%s\047%s\047", (NR==1?"":", "), $0 } END{ print "" }')]" >> $GITHUB_OUTPUT
    - run: echo "matrix=[$(ls -A1 moto | grep -v '.py' | awk '{ printf "%s\047%s\047", (NR==1?"":", "), $0 } END{ print "" }')]"
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
  runtest:
    name: Run Dependency Test
    runs-on: ubuntu-latest
    needs: prepare_list
    strategy:
      matrix:
        python-version: [ 3.8 ]
        service: ${{ fromJson(needs.prepare_list.outputs.matrix) }}

    steps:
    - name: Checkout repo
      uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Run test
      env:
        AWS_ACCESS_KEY_ID: key
        AWS_SECRET_ACCESS_KEY: secret
      run: |
        scripts/dependency_test.sh ${{ matrix.service }}
