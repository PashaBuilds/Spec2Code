/*
 * vitis_which_stub.c - GUI-subsystem "which" replacement for the Vitis XSCT flow.
 *
 * Build (MSVC, from a vcvars64 prompt):
 *   cl /nologo /O1 /GS- vitis_which_stub.c /link /SUBSYSTEM:WINDOWS /ENTRY:shimEntry /NODEFAULTLIB kernel32.lib /OUT:which.exe
 *
 * Usage: back up <Vitis>/gnuwin/bin/which.exe and drop this build in its place
 * on hosts where `app create` hangs with a stuck `which sdscc` child
 * (S2C-VITIS-HANG-010). See kimi_vitis_debug_guide.md section 7.
 *
 * Vitis 2023.2 SDSCorePlugin.start() runs `which sdscc` via Java Runtime.exec
 * and blocks on readLine() until the child exits. On some Windows hosts a
 * console child spawned from the (console-less) Vitis cmdline service
 * deadlocks inside console initialisation before reaching main(), which hangs
 * `app create` forever. This shim is linked as a GUI-subsystem binary so no
 * conhost is ever created; it mimics `which`: prints the resolved path and
 * exits 0 when found, exits 1 otherwise.
 */
#include <windows.h>

static void shimWrite(HANDLE hOut, const char* cpText, DWORD ulLength)
{
    DWORD ulWritten = 0;

    if ((hOut != NULL) && (hOut != INVALID_HANDLE_VALUE))
    {
        WriteFile(hOut, cpText, ulLength, &ulWritten, NULL);
    }
}

void shimEntry(void)
{
    char* cpCommand = GetCommandLineA();
    char cArrName[512];
    char cArrFound[MAX_PATH];
    char* cpFilePart = NULL;
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    int iIndex = 0;

    /* Skip the (possibly quoted) program token. */
    if (*cpCommand == '"')
    {
        cpCommand++;
        while ((*cpCommand != '\0') && (*cpCommand != '"'))
        {
            cpCommand++;
        }
        if (*cpCommand == '"')
        {
            cpCommand++;
        }
    }
    else
    {
        while ((*cpCommand != '\0') && (*cpCommand != ' ') && (*cpCommand != '\t'))
        {
            cpCommand++;
        }
    }
    while ((*cpCommand == ' ') || (*cpCommand == '\t'))
    {
        cpCommand++;
    }

    while ((*cpCommand != '\0') && (*cpCommand != ' ') && (*cpCommand != '\t') && (iIndex < 500))
    {
        cArrName[iIndex] = *cpCommand;
        iIndex++;
        cpCommand++;
    }
    cArrName[iIndex] = '\0';

    if (iIndex == 0)
    {
        ExitProcess(1);
    }

    {
        DWORD ulFound = SearchPathA(NULL, cArrName, ".exe", MAX_PATH, cArrFound, &cpFilePart);

        if ((ulFound > 0) && (ulFound < MAX_PATH))
        {
            shimWrite(hOut, cArrFound, ulFound);
            shimWrite(hOut, "\r\n", 2);
            ExitProcess(0);
        }
    }
    ExitProcess(1);
}
