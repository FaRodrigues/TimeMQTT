# Dicionário com opções de alarme e suas descrições
optionsAlarmDict = {
    1: "External reference error",
    2: "Internal oscillator error",
    4: "PLL Lock error",
    8: "Tuning voltage error",
    16: "Invalid parameter",
    32: "Invalid command",
    64: "DC Backup Loss",
    128: "AC Power Loss"
}

# Solicitando ao usuário que insira um número correspondente a um erro
numExibido = int(input("Insira o número correspondente ao erro:\n"))

# Inicializando a lista para armazenar as descrições dos erros ativados
erros_ativados = []

# Percorrendo o dicionário optionsAlarmDict e verificando se a opção está ativada no número inserido
for chave, descricao in optionsAlarmDict.items():
    if chave & numExibido:
        erros_ativados.append(descricao)

# Exibindo as descrições dos erros ativados
if erros_ativados:
    print("Erros ativados:")
    for erro in erros_ativados:
        print(erro)
else:
    print("Nenhum erro ativado para o número inserido.")
