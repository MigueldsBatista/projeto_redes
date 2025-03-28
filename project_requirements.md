# Cliente-Servidor com Transporte Confiável de Dados

## Visão Geral do Projeto
Este documento detalha os passos e requisitos para implementar uma aplicação cliente-servidor que simula transporte confiável de dados na camada de aplicação, mesmo com um canal de comunicação sujeito a perdas e erros.

## Requisitos do Projeto

### Especificações Gerais
- Data de apresentação: 28/05/2025
- Duração da apresentação: 10 minutos
- Pontuação: 0-10, com 0,5 ponto extra para implementação de checagem de integridade

### Funcionalidades Principais
1. Comunicação cliente-servidor via sockets TCP/IP
2. Limite máximo de caracteres por mensagem (definido no início da comunicação)
3. Pacotes com carga útil de no máximo 3 caracteres
4. Apresentação de metadados das mensagens no servidor
5. Exibição de confirmações no cliente

### Características Específicas
1. Conexão via localhost ou IP
2. Protocolo de aplicação definido e documentado
3. Implementação das características de transporte confiável:
   - Soma de verificação
   - Temporizador
   - Número de sequência
   - Reconhecimento
   - Reconhecimento negativo
   - Janela e paralelismo
4. Simulação de falhas de integridade e perdas de mensagens
5. Suporte a envio de pacotes isolados ou em lotes
6. Configuração do servidor para confirmação individual ou em grupo

## Esclarecimento Importante
O projeto **NÃO** requer implementação de um servidor HTTP. A comunicação deve ser feita via sockets TCP/IP diretamente, implementando um protocolo de aplicação personalizado conforme as especificações acima. O objetivo é simular os mecanismos de transporte confiável na camada de aplicação.

## Plano de Implementação

### Etapa 1: Estrutura Básica
- [ ] Configurar servidor socket TCP em C
- [x] Definir formato de pacotes da aplicação
- [ ] Implementar conexão cliente-servidor básica

### Etapa 2: Protocolo de Aplicação
- [ ] Definir formato das requisições e respostas
- [ ] Implementar limite de caracteres por mensagem
- [ ] Implementar pacotes com máximo de 3 caracteres úteis

### Etapa 3: Transporte Confiável
- [ ] Implementar soma de verificação (checksum)
- [ ] Adicionar números de sequência aos pacotes
- [ ] Implementar mecanismo de reconhecimento (ACK)
- [ ] Desenvolver reconhecimento negativo (NACK)
- [ ] Implementar temporizador para retransmissão
- [ ] Desenvolver mecanismo de janela deslizante

### Etapa 4: Tratamento de Erros
- [ ] Implementar simulação de falhas de integridade
- [ ] Adicionar simulação de perdas de pacotes
- [ ] Desenvolver detecção e correção de erros

### Etapa 5: Configuração e Otimização
- [ ] Implementar opções de envio (isolado ou em lotes)
- [ ] Configurar modos de confirmação do servidor
- [ ] Otimizar para diferentes cenários de erro

### Etapa 6: Documentação e Testes
- [ ] Elaborar manual de utilização
- [ ] Documentar protocolo de aplicação
- [ ] Realizar testes em diferentes cenários
- [ ] Preparar apresentação

## Estrutura do Pacote de Aplicação

```
+----------------+----------------+----------------+----------------+
| Sequence (4B)  | Checksum (4B)  | Length (2B)    | Flags (1B)     |
+----------------+----------------+----------------+----------------+
| Timestamp (8B) | Max Chars (2B) | Payload (var)  | ...            |
+----------------+----------------+----------------+----------------+
```

### Campos do Pacote
- **Sequence**: Número de sequência do pacote
- **Checksum**: Soma de verificação para detecção de erros
- **Length**: Tamanho do payload em bytes
- **Flags**: Bits de controle (ACK, NACK, SYN, FIN, etc.)
- **Timestamp**: Momento de envio (para cálculo de timeout)
- **Max Chars**: Limite máximo de caracteres (definido no início)
- **Payload**: Dados úteis (máximo 3 caracteres por pacote)

## Configurações de Simulação de Erro
- Taxa de erro: 0-100% (probabilidade de corromper um pacote)
- Taxa de perda: 0-100% (probabilidade de perder um pacote)
- Atraso: 0-5000ms (simulação de latência da rede)

## Próximos Passos
1. Implementar a estrutura do pacote
2. Desenvolver mecanismo de fragmentação de mensagens
3. Implementar checksum para detecção de erros
4. Adicionar controle de fluxo via janela deslizante
