#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import mock_utils

# Obtém o diretório do script (seguindo links simbólicos)
script_mockshadow_dir = os.path.dirname(os.path.realpath(__file__))

# Carrega as configurações e funções auxiliares
# Presume que env.py e mock_utils.py estão no mesmo diretório do script

# Flags para controlar a execução
run_version = False
run_create_project = False
create_project_name = ""
run_mock = False
run_remock = False
run_build = False
run_rebuild = False
run_exec = False
run_unmock = False
show_details = False
run_debug = False
run_list = False
run_clone_tree = False
run_clone_project = False
run_open_mock = False
open_mock_file = ""

# Processa os argumentos da linha de comando
for arg in sys.argv[1:]:
    if run_create_project:
        create_project_name = arg
        break
    if run_open_mock:
        open_mock_file = arg
        break

    if arg == "version":
        run_version = True
    elif arg == "create-project":
        run_create_project = True
    elif arg == "details":
        show_details = True
    elif arg == "run":
        run_mock = True
        run_build = True
        run_exec = True
    elif arg == "mock":
        run_mock = True
    elif arg == "remock":
        run_remock = True
    elif arg == "build":
        run_build = True
    elif arg == "rebuild":
        run_rebuild = True
    elif arg == "exec":
        run_exec = True
    elif arg == "debug":
        run_debug = True
    elif arg == "unmock":
        run_unmock = True
    elif arg == "list":
        run_list = True
    elif arg == "clone-tree":
        run_clone_tree = True
    elif arg == "clone-project":
        run_clone_project = True
    elif arg == "open-mock":
        run_open_mock = True
    else:
        print(f"Warning: Unknown argument '{arg}'")

# Executa as funções de acordo com as flags
if run_version:
    print("mockshadow version 1.0")
    sys.exit(0)

if run_create_project:
    mock_utils.create_mockshadow_project(create_project_name)
    sys.exit(0)

if run_list:
    mock_utils.list_mocks()
    sys.exit(0)

if run_clone_tree:
    mock_utils.clone_project_tree()
    sys.exit(0)

if run_clone_project:
    mock_utils.clone_project()
    sys.exit(0)

if run_open_mock:
    import open_mock
    open_mock.open_mock(open_mock_file)
    sys.exit(0)

if run_mock or run_remock:
    mock_args = []
    if show_details:
        mock_args.append("details")
    if run_remock:
        mock_args.append("remock")
    mock_utils.mock_project(*mock_args)

if run_build or run_rebuild:
    print("TODO: run_build and run_rebuild")
    """     
    import runtime
    build_dir = os.path.join(runtime.DIR_MOCK_SHADOW_PROJECT, "build")
    # Se rebuild, remove o diretório build
    if run_rebuild:
        # Usa a função já convertida para remover diretórios
        mock_utils.remove_directory( build_dir )
    # Se o diretório build não existir, cria-o
    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
    os.chdir(build_dir)
    print("Generating Makefile with CMake")
    subprocess.run(["cmake", "../"], check=True)
    print("Building Project...")
    subprocess.run(["make"], check=True)
    os.chdir(script_mockshadow_dir) """

if run_exec or run_debug:
    print("TODO: run_exec and run_debug")
    """ 
    import runtime
    print("Executing Target...")
    os.chdir(runtime.DIR_MOCK_SHADOW_PROJECT)
    target_dir=os.path.join(runtime.DIR_MOCK_SHADOW_PROJECT, "build/executable")
    if run_exec:
        subprocess.run([target_dir], check=True)
    else:
        subprocess.run(["gdb", "-q", "--args", target_dir], check=True)
    os.chdir(script_mockshadow_dir) """

if run_unmock:
    mock_utils.unmock_project()

