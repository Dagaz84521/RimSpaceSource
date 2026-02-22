@echo off
setlocal

pushd "%~dp0"
call conda activate rimspace
python llm_server.py

popd
endlocal
