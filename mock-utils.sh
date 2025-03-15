#!/bin/bash
#  Created on: 21 de jan de 2025
#      Author: roger.moschiel

join_path() {
    local path1="$1"
    local path2="$2"

    # Remove barra no final do primeiro caminho, se existir
    path1="${path1%/}"
    # Remove barra no início do segundo caminho, se existir
    path2="${path2#/}"

    # Retorna o caminho corretamente formatado
    echo "$path1/$path2"
}

# Function to check if a directory exists
directory_exists() {
    local dir="$1"
    
    if [ -d "$dir" ]; then
        return 0  # Directory exists (success)
    else
        return 1  # Directory does not exist (failure)
    fi
}

# Function to check if a file exists
file_exists() {
    if [ -f "$1" ]; then
        return 0  # Arquivo existe
    else
        return 1  # Arquivo não existe
    fi
}

# Terminate script if directory does not exist
validate_directory_exists() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
    echo "Error: Directory '$dir' does not exist."
    exit 1
    fi
}

# Terminate script if file does not exist
validate_file_exists() {
    local file="$1"

    if [ ! -f "$file" ]; then
        echo "Error: File '$file' does not exist."
        exit 1
    fi
}

place_directory() {
    local DIR_SOURCE="$1"
    local DIR_PLACEMENT="$2"

    echo "Placing '${DIR_SOURCE}' in '${DIR_PLACEMENT}'"
    validate_directory_exists $DIR_SOURCE
    validate_directory_exists $DIR_PLACEMENT
    cp -a $DIR_SOURCE $DIR_PLACEMENT
}

remove_directory() {
    local DIR="$1"

    echo "Removing directory '${DIR}'"
    if directory_exists "$DIR"; then
        rm -rf $DIR
    fi
}

copy_directory_content() {
    local SRC="$1"
    local DEST="$2"
    
    rm -rf "$DEST"
    mkdir -p "$DEST"
    # Copia o conteudo do projeto para o novo diretório
    cp -r "$SRC/"* "$DEST"
}

clone_project_tree() {
    # Verifica se o diretório de origem existe
    if [ ! -d "$DIR_ORIGINAL_PROJECT" ]; then
        echo "Erro: '$DIR_ORIGINAL_PROJECT' não é um diretório válido."
        exit 1
    fi

    # Clona a arvore de diretorios do projeto em DIR_SHADOW_MOCKS
    find "$DIR_ORIGINAL_PROJECT" -type d -print | while read -r dir; do
        mkdir -p "$DIR_SHADOW_MOCKS/${dir#$DIR_ORIGINAL_PROJECT/}"
    done
}

list_mocks() {
    # Lista todos os arquivos mock (__mock__ ou __additional__)
    echo "Mock List"
    find "$DIR_SHADOW_MOCKS" -type f \( -name "__mock__*" -o -name "__additional__*" \) -print | while read -r arquivo; do
        # Remove tudo antes de 'DIR_MOCK_SHADOW_PROJECT/'
        caminho_relativo="${arquivo#*$DIR_MOCK_SHADOW_PROJECT/}"
        echo "  $caminho_relativo"
    done
    echo "Mock List Complete!"
}

clone_project() {
    echo "Cloning Project $DIR_ORIGINAL_PROJECT" 
    copy_directory_content "$DIR_ORIGINAL_PROJECT" "$DIR_TEMP_PROJECT" 
    echo "Cloning FreeRTOS"
    echo " ***** TODO: DEPENDENCIA DO PROJETO NAO PODE FICAR AQUI ****"
    echo " ***** TODO: DEPENDENCIA DO PROJETO NAO PODE FICAR AQUI ****"
    echo " ***** TODO: DEPENDENCIA DO PROJETO NAO PODE FICAR AQUI ****"
    copy_directory_content "$DIR_MOCK_SHADOW_PROJECT/FreeRTOS" "$DIR_TEMP_PROJECT/FreeRTOS"
    #echo "Cloning FreeRTOS+FAT"
    #copy_directory_content "$SCRIPT_MOCKSHADOW_DIR/FreeRTOS+FAT" "$SCRIPT_MOCKSHADOW_DIR/MOCKED_PROJECT/FreeRTOS+FAT"
    echo "Cloning Complete"
}

replace_text_in_file() {
    local file="$1"
    local old_text="$2"
    local new_text="$3"

    # Verifica se o arquivo existe
    if [ ! -f "$file" ]; then
        echo "Erro: O arquivo '$file' não existe."
        return 1
    fi

    # Substitui todas as ocorrências da string no arquivo (sem depender de formatação de palavras)
    sed -i "s/$old_text/$new_text/g" "$file"

    return 0
}

mount_extractor_extra_args() {
  local custom_extra_args="$1"
  custom_extra_args="${custom_extra_args#"${custom_extra_args%%[![:space:]]*}"}"

  local file_path="$DIR_MOCK_SHADOW_PROJECT/extractor-global-cflags.txt"
  local line
  local extra_args=""

  # Lê o arquivo linha por linha
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Remove caracteres de quebra de linha/carriage return e trim de espaços
    line=$(echo "$line" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # Se a linha não estiver vazia, adiciona
    if [[ -n "$line" ]]; then
      extra_args="$extra_args $line"
    fi
  done < "$file_path"
  
  #adiciona custom extra args
  extra_args="$custom_extra_args $extra_args"

   # Remove espaços extras no início e imprime o resultado em uma única linha
  echo "$(echo "$extra_args" | sed 's/^[[:space:]]*//')"

}

check_file_mock_mode() {
    if [[ ! -f "$1" ]]; then
        echo "none"
        return
    fi
    
    first_line=$(head -n 1 "$1" | tr -d '\r')
    
    if [[ "$first_line" == "//__MOCK_COPY_FILE_CONTENT__" ]]; then
        echo "copy"
    elif [[ "$first_line" == "//__MOCK_DISCARD_FILE_CONTENT__" ]]; then
        echo "discard"
    else
        echo "discard" #default é "discard"
    fi
}

mock_project() {
   # Parse arguments
    local SHOW_DETAILS=false
    local IS_REMOCK=false
    for arg in "$@"; do
        if [ "$arg" == "details" ]; then
            SHOW_DETAILS=true
            continue
        fi
        if [ "$arg" == "remock" ]; then
            IS_REMOCK=true
            continue
        fi
    done

    proj_basename="$(basename "$DIR_ORIGINAL_PROJECT")"

    #antes de mockar, fazemos o unmock do projeto
    if $IS_REMOCK; then
        unmock_project
    fi

    echo "Creating Mock Files ..."
    # Read the last mock timestamp from the file if it exists
    FILE_LAST_MOCK_TIMESTAMP="$DIR_MOCK_SHADOW_PROJECT/last_mock_timestamp.txt"
    if [ -f "$FILE_LAST_MOCK_TIMESTAMP" ]; then
        last_mock_timestamp=$(cat "$FILE_LAST_MOCK_TIMESTAMP")
    else
        last_mock_timestamp=0
    fi
    # Itera sobre todos os arquivos .c e .h que inciem com "__mock__",
    find "$DIR_SHADOW_MOCKS" -type f \( -name "__mock__*.c" -o -name "__mock__*.h" \) -print | while read -r mock_file; do
        MOCK_DIR=$(dirname "$mock_file")
        MOCK_BASENAME="$(basename "$mock_file")"
        ORIGINAL_BASENAME="${MOCK_BASENAME//__mock__/}" # Pega o nome do arquivo sem "__mock__"
        MOCK_FILE_TO_CREATE="$MOCK_DIR/$ORIGINAL_BASENAME"
        #echo "MOCK_DIR=$MOCK_DIR"
        #echo "MOCK_BASENAME=$MOCK_BASENAME"
        #echo "ORIGINAL_BASENAME=$ORIGINAL_BASENAME"
        #echo "MOCK_FILE_TO_CREATE=$MOCK_FILE_TO_CREATE"
        
        #Se o  MOCK_FILE_TO_CREATE nao existe, ou se houve uma alteracao desde o ultimo mock, refaz o arquivo MOCK_FILE_TO_CREATE
        if ! file_exists "$MOCK_FILE_TO_CREATE" || [ "$(stat -c %Y "$mock_file")" -gt "$last_mock_timestamp" ]; then            
            MOCK_MODE=$(check_file_mock_mode "$mock_file")
            echo "  Creating ${MOCK_FILE_TO_CREATE#*$DIR_MOCK_SHADOW_PROJECT/} (MOCK_MODE: $MOCK_MODE)"
            PARTIAL_DIR="${MOCK_DIR#"$DIR_SHADOW_MOCKS"}" # Remove "DIR_SHADOW_MOCKS" do caminho"
            ORIGINAL_FILE="$(join_path "$DIR_ORIGINAL_PROJECT" "$PARTIAL_DIR")"
            ORIGINAL_FILE="$(join_path "$ORIGINAL_FILE" "$ORIGINAL_BASENAME")"
            #echo "  ORIGINAL_FILE=$ORIGINAL_FILE"
            
            validate_file_exists $ORIGINAL_FILE
        
            if [[ $MOCK_MODE == "copy" ]]; then
                # create file MOCK_FILE_TO_CREATE, as a copy of the "original" file
                cp "$ORIGINAL_FILE" "$MOCK_FILE_TO_CREATE"
                # remove "sections of original content"
                mock_remove_content "$mock_file" "$MOCK_FILE_TO_CREATE" $SHOW_DETAILS
                # replace "sections of original content" with "custom content"
                mock_replace_content "$mock_file" "$MOCK_FILE_TO_CREATE" $SHOW_DETAILS
                # insert addition content on top or bottom of the file
                insert_mock_top_bottom "$mock_file" "$MOCK_FILE_TO_CREATE" $SHOW_DETAILS
            else
                # create file MOCK_FILE_TO_CREATE, with "__mock__" file content
                cp "$mock_file" "$MOCK_FILE_TO_CREATE"
                # insert "sections of original content" into the MOCK_FILE_TO_CREATE
                insert_mock_original_content "$ORIGINAL_FILE" "$MOCK_FILE_TO_CREATE" $SHOW_DETAILS
            fi
        fi
    done

    # Write the current timestamp to "last_mock_timestamp.txt"
    last_mock_timestamp=$(date +%s)
    echo "$last_mock_timestamp" > "$FILE_LAST_MOCK_TIMESTAMP"
    echo "Creating Mock Files Complete!"

    echo "Mocking $(basename "$DIR_TEMP_PROJECT") ..."
    # Iterate over the mocks
    find "$DIR_SHADOW_MOCKS" -type f \( -name "*.c" -o -name "*.h" \) ! -name "__mock__*" | while read -r mock_file; do
        proj_file="${mock_file#"$DIR_SHADOW_MOCKS"}" # Remove "DIR_SHADOW_MOCKS" do caminho"
        PROJECT_FILE_TO_REPLACE="$(join_path "$DIR_TEMP_PROJECT" "$proj_file")"
        
        BASENAME_PROJECT_TO_MOCK=$(basename "$DIR_TEMP_PROJECT")
        echo "  Mocking $(join_path "$BASENAME_PROJECT_TO_MOCK" "$proj_file")"

        file_basename="$(basename "$proj_file")"   

        if [[ "$file_basename" =~ ^__additional__ ]]; then
            # se o arquivo comecar com __additional__, ele nao esta substituindo nenhum arquivo original do projeto, 
            # ele deve ser trado como um arquivo ADICIONAL a ser inserido no projeto
            # entao apenas adicionamos o mesmo ao projeto fazendo uma simples copia
            #OBS: o parametro -p, preserva a data da ultima alteração do arquivo, isso evita que 'make' faça rebuild desnecessáarios
            
            #arquivos __additional__ podem estar dentro de pastas adicionais tambem, entao sempre criamos o diretorio antes de copia-los
            mkdir -p $(dirname "$PROJECT_FILE_TO_REPLACE")
            cp -p "$mock_file" "$PROJECT_FILE_TO_REPLACE"
        else
            ORIGINAL_FILE="$(join_path "$DIR_ORIGINAL_PROJECT" "$proj_file")"
            validate_file_exists $ORIGINAL_FILE
            
            # Iremos substituir o arquivo original do projeto, pela versao mockada
            
            #OBS: o parametro -p, preserva a data da ultima alteração do arquivo, isso evita que 'make' faça rebuild desnecessáarios
            cp -p "$mock_file" "$PROJECT_FILE_TO_REPLACE"
        fi
    done
    echo "Mocking $(basename "$DIR_TEMP_PROJECT") Complete!"
}


insert_mock_original_content() {
    # Check if a filename is provided
    if [ $# -lt 2 ]; then
        echo "Usage: <original-source-file> <mock-file-to-create> [boolean show-details]"
    fi

    local SOURCE_FILE="$1"
    local MOCK_FILE_TO_CREATE="$2"
    local SHOW_DETAILS="$3"


    # Check if the file exists
    if [ ! -f "$SOURCE_FILE" ]; then
        echo "Error: Not Found Source File '$SOURCE_FILE' "
        return 1
    fi

    if [ ! -f "$MOCK_FILE_TO_CREATE" ]; then
        echo "Error: Mock File '$MOCK_FILE_TO_CREATE' "
        return 1
    fi

    local TEMPFILE=$(mktemp)

    # Process the mock file line by line and insert new content when pattern is found
    while IFS= read -r line || [[ -n "$line" ]]; do
        echo "$line" >> "$TEMPFILE"
        
        if [[ "$line" =~ __MKO:\ ([^[:space:]]+)[[:space:]]+([^[:space:]]+)([[:space:]]+.*)? ]]; then
            local firstline=$line
            local EXTRACT_TYPE="${BASH_REMATCH[1]}"
            local EXTRACT_NAME="${BASH_REMATCH[2]}"
            local EXTRA_ARGS="${BASH_REMATCH[3]}"    
            EXTRA_ARGS="$(mount_extractor_extra_args "$EXTRA_ARGS")"

            if $SHOW_DETAILS; then
                echo "      Keep original $EXTRACT_TYPE '$EXTRACT_NAME'"
            fi

            # Copy content from the source file, and insert into the mock file
            cd $SCRIPT_MOCKSHADOW_DIR/clang-code-extractor
            set +e
            #echo "./extract.sh $EXTRACT_TYPE $EXTRACT_NAME "$SOURCE_FILE" "$EXTRA_ARGS""
            local TextExtracted=""
            TextExtracted=$(./extract.sh $EXTRACT_TYPE $EXTRACT_NAME "$SOURCE_FILE" "$EXTRA_ARGS")
            status=$? 
            #echo "TextExtracted: $TextExtracted"
            set -e
            cd $SCRIPT_MOCKSHADOW_DIR
            if [ $status -ne 0 ]; then
                echo "Error at mock instruction --> $firstline"
                echo $TextExtracted
                exit $status
            fi
            
            # Insert the new lines below the matched line
            echo -e "$TextExtracted" >> "$TEMPFILE"
        fi
    done < "$MOCK_FILE_TO_CREATE"

    mv "$TEMPFILE" "$MOCK_FILE_TO_CREATE"
}

mock_err_msg() {
    local line_number="$1"
    local file="$2"
    local cmd="$3"
    local msg="$4"
    echo "Error at $file:$line_number"
    echo "Mock instruction: $cmd"
    echo "$msg"
}

mock_remove_content() {
    # Check if a filename is provided
    if [ $# -lt 2 ]; then
        echo "Usage: <__mock__ file> <mock-file-to-create> [boolean show-details]"
    fi

    local MOCK_FILE_CMDS="$1"
    local MOCK_FILE_TO_CREATE="$2"
    local SHOW_DETAILS="$3"


    # Check if the file exists
    if [ ! -f "$MOCK_FILE_CMDS" ]; then
        echo "Error: Not Found Source File '$MOCK_FILE_CMDS' "
        return 1
    fi

    if [ ! -f "$MOCK_FILE_TO_CREATE" ]; then
        echo "Error: Mock File '$MOCK_FILE_TO_CREATE' "
        return 1
    fi

    local count=0
    # Iterar sobre cada linha
    while IFS= read -r line || [[ -n "$line" ]]; do 
        count=$((count + 1))
               
        if [[ "$line" =~ __MOCK_REMOVE:\ ([^[:space:]]+)[[:space:]]+([^[:space:]]+)([[:space:]]+.*)? ]]; then
            #coletas os parametros da instrução de mock //__MOCK_REMOVE: <EXTRACT_TYPE> <name> [extra-args]
            local EXTRACT_TYPE="${BASH_REMATCH[1]}"
            local EXTRACT_NAME="${BASH_REMATCH[2]}"
            local EXTRA_ARGS="${BASH_REMATCH[3]}"
            # Adiciona o arg "lines"
            EXTRA_ARGS="lines $(mount_extractor_extra_args "$EXTRA_ARGS")"

            if $SHOW_DETAILS; then
                echo "      Remove original $EXTRACT_TYPE '$EXTRACT_NAME'"
            fi

            ###### EXTRACT CONTENT LINES POSITION ######
            local TextExtracted=""
            EXTRACTOR_DIR=$SCRIPT_MOCKSHADOW_DIR/clang-code-extractor
            cd $EXTRACTOR_DIR
            set +e
            TextExtracted=$(./extract.sh $EXTRACT_TYPE $EXTRACT_NAME "$MOCK_FILE_TO_CREATE" $EXTRA_ARGS)
            status=$?
            set -e
            cd $SCRIPT_MOCKSHADOW_DIR
            if [ $status -ne 0 ]; then
                mock_err_msg "$count" "$MOCK_FILE_CMDS" "$line" "$TextExtracted"
                exit $status
            fi

            # Faz o split por ";" de "<line_start>;<line_end>" para as variaveis START_LINE e END_LINE
            IFS=';' read -r START_LINE END_LINE <<< "$TextExtracted"
            #echo "Start: $START_LINE, End: $END_LINE"

            ###### REMOVE CUSTOM CONTENTE FROM START_LINE POSITION ######
            # Substiui o conteudo da linha inicial e final, pela instrução //__MOCK_REMOVE: <type> <name>
            # Criar um arquivo temporário com as substituições, e atualiza MOCK_FILE_TO_CREATE com o arquivo temporario
            awk -v start="$START_LINE" -v end="$END_LINE" -v block="$line" '
            NR < start { print }
            NR == start { print block }
            NR > end { print }
            ' "$MOCK_FILE_TO_CREATE" > temp_file && mv temp_file "$MOCK_FILE_TO_CREATE"
        fi
    done < "$MOCK_FILE_CMDS"
}


mock_replace_content() {
    # Check if a filename is provided
    if [ $# -lt 2 ]; then
        echo "Usage: <__mock__ file> <mock-file-to-create> [boolean show-details]"
    fi

    local MOCK_FILE_CMDS="$1"
    local MOCK_FILE_TO_CREATE="$2"
    local SHOW_DETAILS="$3"


    # Check if the file exists
    if [ ! -f "$MOCK_FILE_CMDS" ]; then
        echo "Error: Not Found Source File '$MOCK_FILE_CMDS' "
        return 1
    fi

    if [ ! -f "$MOCK_FILE_TO_CREATE" ]; then
        echo "Error: Mock File '$MOCK_FILE_TO_CREATE' "
        return 1
    fi

    # Variável para controlar se estamos dentro de um bloco
    local inside_mock_block=false
    local MOCK_CMD=""

    # Iterar sobre cada linha
    local count=0
    local SRC_START_LINE=0
    local SRC_END_LINE=0
    local REPLACE_MODE=""
    while IFS= read -r line || [[ -n "$line" ]]; do       
        count=$((count + 1))

        if [[ "$line" =~ __MOCK_REPLACE_(START|LINE):\ ([^[:space:]]+)[[:space:]]+([^[:space:]]+)([[:space:]]+.*)? ]]; then
            if [ "$inside_mock_block" == true ]; then
                mock_err_msg "$count" "$MOCK_FILE_CMDS" "$line" "Nested instruction, expected __MOCK_REPLACE_END"
                exit 1
            fi
            inside_mock_block=true
            MOCK_CMD="$line"
            SRC_START_LINE=$count

            #coletas os parametros da instrução de mock //__MOCK_REPLACE_(START|LINE): <EXTRACT_TYPE> <name> [extra-args]
            REPLACE_MODE="${BASH_REMATCH[1]}"
            local EXTRACT_TYPE="${BASH_REMATCH[2]}"
            local EXTRACT_NAME="${BASH_REMATCH[3]}"
            local EXTRA_ARGS="${BASH_REMATCH[4]}"
            # Adiciona o arg "lines"
            EXTRA_ARGS="lines $(mount_extractor_extra_args "$EXTRA_ARGS")"

            if $SHOW_DETAILS; then
                echo "      replace original $EXTRACT_TYPE '$EXTRACT_NAME'"
            fi
        elif { [[ "$line" =~ ^//__MOCK_REPLACE_END$ ]] || [[ "$REPLACE_MODE" == "LINE" ]]; }; then          
            if [ "$inside_mock_block" == false ]; then
                mock_err_msg "$count" "$MOCK_FILE_CMDS" "$line" "Missing initial __MOCK_REPLACE_START:"
                exit 1
            fi
            REPLACE_MODE="" #reset
            inside_mock_block=false
            SRC_END_LINE=$count

            ###### DESCOBRE AS LINHA DO ARQUIVO DE DESTINO "DEST_START_LINE" e "DEST_END_LINE" ######
            local TextExtracted=""
            EXTRACTOR_DIR=$SCRIPT_MOCKSHADOW_DIR/clang-code-extractor
            cd $EXTRACTOR_DIR
            
            set +e
            TextExtracted=$(./extract.sh $EXTRACT_TYPE $EXTRACT_NAME "$MOCK_FILE_TO_CREATE" $EXTRA_ARGS)
            status=$?
            set -e
            cd $SCRIPT_MOCKSHADOW_DIR
            if [ $status -ne 0 ]; then
                mock_err_msg "$count" "$MOCK_FILE_CMDS" "$MOCK_CMD" "$TextExtracted"
                exit $status
            fi
            # Faz o split por ";" de "<line_start>;<line_end>" para as variaveis DEST_START_LINE e DEST_END_LINE
            IFS=';' read -r DEST_START_LINE DEST_END_LINE <<< "$TextExtracted"
            #echo "SRC Start: $SRC_START_LINE, End: $SRC_END_LINE"
            #echo "DEST Start: $DEST_START_LINE, End: $DEST_END_LINE"

            # PEGAMOS O CONTEUDO DO ARQUIVO FONTE ENTRE AS LINHAS SRC_START_LINE & SRC_END_LINE
            # E TRANSFERIMOS PARA UM ARQUIVO TEMPORARIO, 
            # (NAO DA PRA DEIXAR SALVO EM VARIAVEL NO SHELL, DEVIDO A CARACTERES DE ESCAPE, DEVIA TER FEITO ESSA MERDA EM PYTHON)
            local TEMP_FILE="/tmp/${EXTRACT_TYPE}_${EXTRACT_NAME}.tmp"
            sed -n "${SRC_START_LINE},${SRC_END_LINE}p" "$MOCK_FILE_CMDS" > $TEMP_FILE


            ###### REPLACE CUSTOM CONTENTE INTO DEST_START_LINE POSITION ######
            # Substiui o conteudo da linha inicial e final, pelo conteudo customizado
            # Criar um arquivo temporário com as substituições, e atualiza MOCK_FILE_TO_CREATE com o arquivo temporario
            awk -v start="${DEST_START_LINE}" \
                -v end="${DEST_END_LINE}" \
                -v tmpfile="$TEMP_FILE" '
            NR < start {
                print
            }
            NR == start {
                # Lê o conteúdo do arquivo temporário e imprime aqui
                while ((getline line < tmpfile) > 0) {
                print line
                }
                close(tmpfile)
            }
            NR > end {
                print
            }
            ' "$MOCK_FILE_TO_CREATE" > temp_file && mv temp_file "$MOCK_FILE_TO_CREATE"
        fi
    done < "$MOCK_FILE_CMDS"
    
    if [ "$inside_mock_block" == true ]; then
        mock_err_msg "$count" "$MOCK_FILE_CMDS" "$MOCK_CMD" "Missing __MOCK_REPLACE_END"
        exit 1
    fi
}

insert_mock_top_bottom() {
    # Verifica se foram passados pelo menos 2 parâmetros
    if [ $# -lt 2 ]; then
        echo "Usage: <__mock__ file> <mock-file-to-create> [boolean show-details]"
        return 1
    fi

    local MOCK_FILE_CMDS="$1"
    local MOCK_FILE_TO_CREATE="$2"
    local SHOW_DETAILS="$3"

    # Verifica se os arquivos existem
    if [ ! -f "$MOCK_FILE_CMDS" ]; then
        echo "Error: Not Found Source File '$MOCK_FILE_CMDS' "
        return 1
    fi

    if [ ! -f "$MOCK_FILE_TO_CREATE" ]; then
        echo "Error: Mock File '$MOCK_FILE_TO_CREATE' "
        return 1
    fi

    # Variável única de controle para bloco
    local inside_block=false
    local block_type=""
    local MOCK_CMD=""
    local count=0
    local SRC_START_LINE=0
    local SRC_END_LINE=0
    local DEST_START_LINE=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        count=$((count + 1))

        # Verifica se a linha indica início de um bloco (top ou bottom)
        if [[ "$line" =~ ^//__(MOCK_TOP|MOCK_BOTTOM)_START$ ]]; then
            if [ "$inside_block" = true ]; then
                echo "Erro: Bloco aninhado detectado em linha $count. Não permitido."
                exit 1
            fi
            inside_block=true
            block_type=$(echo "$line" | sed 's,//__\(MOCK_[A-Z]*\)_START,\1,')
            MOCK_CMD="$line"
            SRC_START_LINE=$count

            if [ "$SHOW_DETAILS" = true ]; then
                if [ "$block_type" = "MOCK_BOTTOM" ]; then
                    echo "      insert content at the BOTTOM"
                elif [ "$block_type" = "MOCK_TOP" ]; then
                    echo "      insert content at the TOP"
                fi
            fi

        # Verifica se é o marcador de fim correspondente (top ou bottom)
        elif [[ "$line" =~ ^//__(MOCK_TOP|MOCK_BOTTOM)_END$ ]]; then
            if [ "$inside_block" = false ]; then
                echo "Erro: Marcador de fim encontrado sem bloco iniciado (linha $count)."
                exit 1
            fi

            local expected_end="//__${block_type}_END"
            if [ "$line" != "$expected_end" ]; then
                echo "Erro: Marcador de fim '$line' não corresponde ao início '$MOCK_CMD' (linha $count)."
                exit 1
            fi

            inside_block=false
            SRC_END_LINE=$count

            # Extrai o conteúdo do bloco do arquivo de comandos
            local TEMP_FILE="/tmp/${block_type}_$(basename "$MOCK_FILE_TO_CREATE").tmp"
            sed -n "${SRC_START_LINE},${SRC_END_LINE}p" "$MOCK_FILE_CMDS" > "$TEMP_FILE"

            # Determina a linha de destino com base no tipo do bloco
            if [ "$block_type" = "MOCK_BOTTOM" ]; then
                if [[ "$MOCK_FILE_TO_CREATE" == *.h ]]; then
                    DEST_START_LINE=$(grep -n "#endif" "$MOCK_FILE_TO_CREATE" | tail -n1 | cut -d: -f1)
                    if [ -z "$DEST_START_LINE" ]; then
                        echo "Aviso: Nenhum #endif encontrado. Inserindo no final do arquivo."
                        DEST_START_LINE=$(wc -l < "$MOCK_FILE_TO_CREATE")
                    else
                        DEST_START_LINE=$((DEST_START_LINE - 1))
                    fi
                else
                    DEST_START_LINE=$(wc -l < "$MOCK_FILE_TO_CREATE")
                fi
            elif [ "$block_type" = "MOCK_TOP" ]; then
                if [[ "$MOCK_FILE_TO_CREATE" == *.h ]]; then
                    DEST_START_LINE=$(grep -n "^#define" "$MOCK_FILE_TO_CREATE" | head -n1 | cut -d: -f1)
                    if [ -z "$DEST_START_LINE" ]; then
                        DEST_START_LINE=1
                    else
                        DEST_START_LINE=$((DEST_START_LINE + 1))
                    fi
                else
                    DEST_START_LINE=1
                fi
            fi

            # Insere o conteúdo extraído no arquivo de destino usando awk
            awk -v start="${DEST_START_LINE}" -v tmpfile="$TEMP_FILE" '
                NR < start { print }
                NR == start {
                    while ((getline line < tmpfile) > 0) {
                        print line
                    }
                    close(tmpfile)
                }
                NR >= start { print }
            ' "$MOCK_FILE_TO_CREATE" > temp_file && mv temp_file "$MOCK_FILE_TO_CREATE"
        fi
    done < "$MOCK_FILE_CMDS"

    if [ "$inside_block" = true ]; then
        echo "Erro: Bloco iniciado com '$MOCK_CMD' não foi encerrado corretamente."
        exit 1
    fi
}


unmock_project() {
    # Itera sobre todos os arquivos
    echo "Cleaning $(basename "$DIR_SHADOW_MOCKS") ..."
    find "$DIR_SHADOW_MOCKS" -type f \( -name "*.c" -o -name "*.h" \) \
        ! -name "__mock__*" \
        ! -name "__additional__*" | while read -r mock_file; do
            rm "$mock_file"
            echo "  Removed ${mock_file#*$DIR_MOCK_SHADOW_PROJECT/} "
    done
    echo "Cleaning Complete!"

    clone_project
}
