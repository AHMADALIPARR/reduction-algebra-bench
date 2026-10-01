CC ?= gcc
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -Werror -Iinclude
LDFLAGS ?= -lcrypto
BIN=rarbench
all: $(BIN) test
$(BIN): src/reduction.c src/main.c include/reduction.h
	$(CC) $(CFLAGS) src/reduction.c src/main.c -o $@ $(LDFLAGS)
test: src/reduction.c tests/test.c include/reduction.h
	$(CC) $(CFLAGS) src/reduction.c tests/test.c -o test $(LDFLAGS)
clean:
	rm -f $(BIN) test
