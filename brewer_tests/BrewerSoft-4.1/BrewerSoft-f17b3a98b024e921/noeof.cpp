//---------------------------------------------------------------------------

#pragma hdrstop
#include <stdio.h>
//---------------------------------------------------------------------------

#pragma argsused
int main(int argc, char* argv[])
{
 FILE *in, *out;
 char c;
    if( argc<2 ) {printf("One parameter required: file name. The same file will be written with all charachters x1a (EOF) removed.");return 1;}

    in = fopen(argv[1],"rb");
    out = fopen("tmp.tmp","wb");
    while( !feof(in) )
           {
               c=fgetc(in);
               if( feof(in) ) break;
               if( c==0x1a ) continue;
               fputc(c,out);
           }
     fclose(in);
     fclose(out);
        return 0;
}
//---------------------------------------------------------------------------
 