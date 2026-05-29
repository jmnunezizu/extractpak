#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <ctype.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <dirent.h>
#include <sys/stat.h>
#include <libgen.h>


#define WRITE_DDS

#define DWORD uint32_t

#define DDSD_CAPS                       0x00000001
#define DDSD_HEIGHT                     0x00000002
#define DDSD_WIDTH                      0x00000004
#define DDSD_PITCH                      0x00000008
#define DDSD_PIXELFORMAT                0x00001000
#define DDSD_MIPMAPCOUNT                0x00020000
#define DDSD_LINEARSIZE                 0x00080000
#define DDSD_DEPTH                      0x00800000
#define DDPF_ALPHAPIXELS                0x00000001
#define DDPF_FOURCC                     0x00000004
#define DDPF_RGB                        0x00000040
#define DDSCAPS_COMPLEX                 0x00000008
#define DDSCAPS_TEXTURE                 0x00001000
#define DDSCAPS_MIPMAP                  0x00400000
#define DDSCAPS2_CUBEMAP                0x00000200
#define DDSCAPS2_CUBEMAP_POSITIVEX      0x00000400
#define DDSCAPS2_CUBEMAP_NEGATIVEX      0x00000800
#define DDSCAPS2_CUBEMAP_POSITIVEY      0x00001000
#define DDSCAPS2_CUBEMAP_NEGATIVEY      0x00002000
#define DDSCAPS2_CUBEMAP_POSITIVEZ      0x00004000
#define DDSCAPS2_CUBEMAP_NEGATIVEZ      0x00008000
#define DDSCAPS2_VOLUME                 0x00200000

typedef struct {
    DWORD dwMagic;
    DWORD dwSize;
    DWORD dwFlags;
    DWORD dwHeight;
    DWORD dwWidth;
    DWORD dwPitchOrLinearSize;
    DWORD dwDepth;
    DWORD dwMipMapCount;
    DWORD dwReserved1[11];
    /*  DDPIXELFORMAT   */
    struct {
        DWORD dwSize;
        DWORD dwFlags;
        DWORD dwFourCC;
        DWORD dwRGBBitCount;
        DWORD dwRBitMask;
        DWORD dwGBitMask;
        DWORD dwBBitMask;
        DWORD dwAlphaBitMask;
    } sPixelFormat;
    /*  DDCAPS2 */
    struct {
        DWORD dwCaps1;
        DWORD dwCaps2;
        DWORD dwDDSX;
        DWORD dwReserved;
    } sCaps;
    DWORD dwReserved2;
} DDS_header;


typedef struct PakHeader {
    DWORD magic;                /* KAPL -> "LPAK" */
    float version;
    DWORD startOfIndex;         /* -> 1 DWORD per file */
    DWORD startOfFileEntries;   /* -> 5 DWORD per file */
    DWORD startOfFileNames;     /* zero-terminated string */
    DWORD startOfData;
    DWORD sizeOfIndex;
    DWORD sizeOfFileEntries;
    DWORD sizeOfFileNames;
    DWORD sizeOfData;
} PakHeader;

typedef struct PakFileEntry {
    DWORD fileDataPos;          /* + startOfData */
    DWORD fileNamePos;          /* older parser treated this as + startOfFileNames */
    DWORD dataSize;
    DWORD dataSize2;            /* real size? (always =dataSize) */
    DWORD compressed;           /* compressed? (always 0) */
} PakFileEntry;

static int read_name(FILE *file, const PakHeader *header, DWORD nameOffset, char *name, size_t nameSize)
{
    DWORD relativeOffset = nameOffset;

    if (nameSize == 0)
        return -1;
    name[0] = '\0';
    if (relativeOffset >= header->sizeOfFileNames &&
        nameOffset >= header->startOfFileNames &&
        nameOffset < header->startOfFileNames + header->sizeOfFileNames)
        relativeOffset = nameOffset - header->startOfFileNames;
    if (relativeOffset >= header->sizeOfFileNames)
        return -1;
    if (fseek(file, header->startOfFileNames + relativeOffset, SEEK_SET) != 0)
        return -1;
    if (fgets(name, (int) nameSize, file) == NULL)
        return -1;
    name[nameSize - 1] = '\0';
    return 0;
}

static unsigned int read_name_table_offsets(FILE *file, const PakHeader *header, DWORD **offsets)
{
    char *nameTable;
    unsigned int count = 0;
    DWORD pos = 0;
    DWORD capacity = header->sizeOfFileNames / 2 + 1;

    *offsets = NULL;
    if (header->sizeOfFileNames == 0)
        return 0;

    nameTable = malloc(header->sizeOfFileNames);
    if (nameTable == NULL)
        return 0;

    *offsets = malloc(capacity * sizeof(DWORD));
    if (*offsets == NULL) {
        free(nameTable);
        return 0;
    }

    if (fseek(file, header->startOfFileNames, SEEK_SET) != 0 ||
        fread(nameTable, header->sizeOfFileNames, 1, file) != 1) {
        free(nameTable);
        free(*offsets);
        *offsets = NULL;
        return 0;
    }

    while (pos < header->sizeOfFileNames) {
        DWORD start = pos;
        if (count >= capacity) {
            DWORD newCapacity = capacity * 2;
            DWORD *newOffsets = realloc(*offsets, newCapacity * sizeof(DWORD));
            if (newOffsets == NULL)
                break;
            *offsets = newOffsets;
            capacity = newCapacity;
        }
        (*offsets)[count++] = start;
        while (pos < header->sizeOfFileNames && nameTable[pos] != '\0')
            pos++;
        if (pos >= header->sizeOfFileNames)
            break;
        pos++;
    }

    free(nameTable);
    return count;
}

static void print_usage(const char *program)
{
    printf("Usage:\n");
    printf("  %s --list <pak file>\n", program);
    printf("  %s --debug-classic <pak file>\n", program);
    printf("  %s [--only text] <pak file> [output_dir]\n", program);
}

static int resolve_name(FILE *file, const PakHeader *header, const PakFileEntry *entry,
                        DWORD *nameOffsets, unsigned int numNameOffsets,
                        unsigned int index, char *name, size_t nameSize,
                        DWORD *rawNameOffset)
{
    if (index < numNameOffsets) {
        *rawNameOffset = nameOffsets[index];
        if (read_name(file, header, *rawNameOffset, name, nameSize) == 0)
            return 0;
    }

    *rawNameOffset = entry->fileNamePos;
    return read_name(file, header, *rawNameOffset, name, nameSize);
}

static int make_output_path(char *dest, size_t destSize, const char *outputDir, const char *relativePath)
{
    int written;

    if (outputDir == NULL || outputDir[0] == '\0' || strcmp(outputDir, ".") == 0) {
        written = snprintf(dest, destSize, "%s", relativePath);
    } else {
        size_t len = strlen(outputDir);
        if (len > 0 && outputDir[len - 1] == '/')
            written = snprintf(dest, destSize, "%s%s", outputDir, relativePath);
        else
            written = snprintf(dest, destSize, "%s/%s", outputDir, relativePath);
    }

    return written >= 0 && (size_t) written < destSize ? 0 : -1;
}

/* Recursive mkdir from http://nion.modprobe.de/blog/archives/357-Recursive-directory-creation.html */
static void _mkdir2(const char *path)
{
    char opath[256];
    char *p;
    size_t len;

    if (path == NULL || path[0] == '\0' || strcmp(path, ".") == 0)
        return;

    strncpy(opath, path, sizeof(opath) - 1);
    opath[sizeof(opath) - 1] = '\0';
    len = strlen(opath);
    if (len == 0)
        return;
    if (opath[len - 1] == '/')
        opath[len - 1] = '\0';
    for (p = opath; *p; p++)
        if (*p == '/') {
            *p = '\0';
            if (access(opath, F_OK))
                mkdir(opath, S_IRWXU);
            *p = '/';
        }
    if (access(opath, F_OK))    /* if path is not terminated with / */
        mkdir(opath, S_IRWXU);
}

/* Write out a dds file from dxt data */
int write_dds(char *fileName, char *DDS_data, DWORD DDS_size)
{
    DDS_header header;
    FILE *fout;
    DWORD *int_data = (DWORD *) DDS_data;
    DDS_size -= 12;
    DDS_data += 12;
    memset(&header, 0, sizeof(DDS_header));
    header.dwMagic = ('D' << 0) | ('D' << 8) | ('S' << 16) | (' ' << 24);
    header.sPixelFormat.dwFourCC = int_data[0];
    header.dwWidth = int_data[1];
    header.dwHeight = int_data[2];
    header.dwSize = 124;
    header.dwFlags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE;
    header.dwPitchOrLinearSize = DDS_size;
    header.sPixelFormat.dwSize = 32;
    header.sPixelFormat.dwFlags = DDPF_FOURCC;
    header.sCaps.dwCaps1 = DDSCAPS_TEXTURE;
    fout = fopen(fileName, "wb");
    if (fout == NULL) {
        printf("Could not write to %s\n", fileName);
        return -1;
    }
    fwrite(&header, sizeof(DDS_header), 1, fout);
    fwrite(DDS_data, 1, DDS_size, fout);
    fclose(fout);
    return 0;
}

int main(int argc, char **argv)
{
    PakHeader header;
    PakFileEntry *entries;
    DWORD *nameOffsets;
    char rawName[FILENAME_MAX];
    char outName[FILENAME_MAX];
    char writeName[FILENAME_MAX];
    char ddsName[FILENAME_MAX];
    char dirName[FILENAME_MAX];
    const char *archiveName;
    const char *outputDir = NULL;
    const char *filter = NULL;
    unsigned int numEntries;
    unsigned int numIndexRecords;
    unsigned int numFileEntries;
    unsigned int numNameOffsets;
    unsigned int i;
    int len;
    int listOnly = 0;
    int diagOnly = 0;
    int convertDds = 1;
    FILE *outFile;
    FILE *file;
    char *buffer;
    unsigned int extracted = 0;
    unsigned int skipped = 0;
    unsigned int failed = 0;
    unsigned int matched = 0;

    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    if (strcmp(argv[1], "--list") == 0) {
        if (argc != 3) {
            print_usage(argv[0]);
            return 1;
        }
        listOnly = 1;
        archiveName = argv[2];
    } else if (strcmp(argv[1], "--debug-classic") == 0 || strcmp(argv[1], "--diag") == 0) {
        if (argc != 3) {
            print_usage(argv[0]);
            return 1;
        }
        diagOnly = 1;
        archiveName = argv[2];
    } else if (strcmp(argv[1], "--only") == 0) {
        if (argc < 4 || argc > 5) {
            print_usage(argv[0]);
            return 1;
        }
        filter = argv[2];
        archiveName = argv[3];
        if (argc == 5)
            outputDir = argv[4];
        if (strcmp(filter, "classic/en") == 0)
            convertDds = 0;
    } else if (strncmp(argv[1], "--", 2) == 0) {
        printf("Unknown option: %s\n", argv[1]);
        print_usage(argv[0]);
        return 1;
    } else {
        if (argc > 3) {
            print_usage(argv[0]);
            return 1;
        }
        archiveName = argv[1];
        if (argc == 3)
            outputDir = argv[2];
    }

    if ((file = fopen(archiveName, "rb")) == NULL) {
        printf("Could not open file: %s\n", archiveName);
        return -1;
    }
    /* Read header */
    fread(&header, sizeof(PakHeader), 1, file);
    /* Read filename table string starts and file entries */
    numIndexRecords = header.sizeOfIndex / sizeof(DWORD);
    numFileEntries = header.sizeOfFileEntries / sizeof(PakFileEntry);
    numNameOffsets = read_name_table_offsets(file, &header, &nameOffsets);
    if (nameOffsets == NULL || numNameOffsets == 0) {
        printf("Could not read filename table.\n");
        fclose(file);
        return -1;
    }
    numEntries = numFileEntries;
    if (numNameOffsets < numEntries)
        numEntries = numNameOffsets;

    entries = malloc(header.sizeOfFileEntries);
    if (entries == NULL) {
        printf("Could not allocate memory for file entries.\n");
        free(nameOffsets);
        fclose(file);
        return -1;
    }
    fseek(file, header.startOfFileEntries, SEEK_SET);
    fread(entries, header.sizeOfFileEntries, 1, file);
    if (diagOnly) {
        printf("index_records=%u name_records=%u file_records=%u parsed_records=%u\n",
               numIndexRecords, numNameOffsets, numFileEntries, numEntries);
        printf("start_of_index=%u start_of_file_entries=%u start_of_file_names=%u start_of_data=%u\n",
               header.startOfIndex, header.startOfFileEntries, header.startOfFileNames, header.startOfData);
    }

    /* Dump files */
    for (i = 0; i < numFileEntries; i++) {
        DWORD nameOffset = 0;
        int haveName = 0;

        haveName = resolve_name(file, &header, &entries[i], nameOffsets, numNameOffsets,
                                i, rawName, sizeof(rawName), &nameOffset) == 0;

        if (diagOnly) {
            printf("record=%u name_offset=", i);
            if (haveName)
                printf("%u", nameOffset);
            else
                printf("<missing>");
            printf(" resolved_name=%s data_offset=%u compressed_size=%u uncompressed_size=%u flags_type=%u entry_field_1=%u\n",
                   haveName ? rawName : "<unresolved>",
                   entries[i].fileDataPos + header.startOfData,
                   entries[i].dataSize, entries[i].dataSize2, entries[i].compressed, entries[i].fileNamePos);
            if (haveName && strstr(rawName, "classic/en/monkey") != NULL) {
                printf("MATCH classic/en/monkey record=%u name_offset=%u resolved_name=%s data_offset=%u compressed_size=%u uncompressed_size=%u flags_type=%u entry_field_1=%u\n",
                       i, nameOffset, rawName, entries[i].fileDataPos + header.startOfData,
                       entries[i].dataSize, entries[i].dataSize2, entries[i].compressed, entries[i].fileNamePos);
            }
            continue;
        }

        if (!haveName) {
            skipped++;
            continue;
        }

        if (listOnly) {
            printf("%s\n", rawName);
            continue;
        }

        if (filter != NULL && strstr(rawName, filter) == NULL)
            continue;

        matched++;
        strncpy(outName, rawName, sizeof(outName) - 1);
        outName[sizeof(outName) - 1] = '\0';
        while (outName[0] == '/')
            memmove(outName, outName + 1, strlen(outName));

        if (outName[0] == '\0') {
            skipped++;
            continue;
        }
        if (make_output_path(writeName, sizeof(writeName), outputDir, outName) != 0) {
            printf("Output path too long: %s\n", outName);
            failed++;
            continue;
        }
        printf("Extracting %s...\n", writeName);
        strncpy(dirName, writeName, sizeof(dirName) - 1);
        dirName[sizeof(dirName) - 1] = '\0';
        _mkdir2((char *) dirname(dirName));
        fseek(file, entries[i].fileDataPos + header.startOfData, SEEK_SET);
        buffer = malloc(entries[i].dataSize);
        if (buffer == NULL) {
            printf("Could not allocate memory for %s\n", writeName);
            failed++;
            continue;
        }
        fread(buffer, entries[i].dataSize, 1, file);
        if ((outFile = fopen(writeName, "wb")) == NULL) {
            printf("Could not write to %s\n", writeName);
            failed++;
            free(buffer);
            continue;
        }
        fwrite(buffer, entries[i].dataSize, 1, outFile);
        fclose(outFile);
        extracted++;
#ifdef WRITE_DDS
        /* Store dxt files in dds container */
        len = strlen(writeName);
        if (convertDds && len >= 3 && writeName[len - 3] == 'd' && writeName[len - 2] == 'x' && writeName[len - 1] == 't') {
            strncpy(ddsName, writeName, sizeof(ddsName) - 1);
            ddsName[sizeof(ddsName) - 1] = '\0';
            ddsName[len - 2] = 'd';
            ddsName[len - 1] = 's';
            printf("Writing %s...\n", ddsName);
            if (write_dds(ddsName, buffer, entries[i].dataSize) != 0)
                failed++;
        }
#endif
        free(buffer);
    }
    fclose(file);
    free(entries);
    free(nameOffsets);
    if (listOnly)
        return 0;
    if (diagOnly)
        return 0;
    if (filter != NULL && matched == 0 && strcmp(filter, "classic/en") == 0)
        printf("No classic/en entries found in the archive index.\n");
    printf("Extracted %u files\n", extracted);
    printf("Skipped %u entries\n", skipped);
    printf("Failed %u files\n", failed);
    return 0;
}
