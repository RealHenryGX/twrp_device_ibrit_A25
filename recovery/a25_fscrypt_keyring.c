/* Create the session keyring expected by Android's vold fscrypt code. */
#include <errno.h>
#include <linux/keyctl.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>

int main(void) {
    long serial = syscall(__NR_add_key, "keyring", "fscrypt", NULL, 0,
                          KEY_SPEC_SESSION_KEYRING);
    if (serial < 0) {
        perror("add_key(fscrypt)");
        return 1;
    }
    printf("fscrypt session keyring ready: %ld\n", serial);
    return 0;
}
