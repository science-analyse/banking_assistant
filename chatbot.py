"""
Interactive Chatbot for Bank of Baku Card Information
"""

from rag_system_simple import BankCardRAG
import sys


def print_banner():
    """Print chatbot banner"""
    print("\n" + "=" * 60)
    print("🏦 Bank of Baku Kart Məlumat Köməkçisi")
    print("=" * 60)
    print("\nMən Bank of Baku-nun kredit və debet kartları haqqında")
    print("suallarınıza cavab verə bilərəm.\n")
    print("Komandalar:")
    print("  'çıxış' və ya 'exit' - Proqramdan çıxmaq")
    print("  'yardım' və ya 'help' - Köməyi göstər")
    print("=" * 60 + "\n")


def print_help():
    """Print help message"""
    print("\n📚 Nümunə Suallar:\n")
    examples = [
        "Bolkart kredit kartının şərtləri nələrdir?",
        "Maaş kartı ilə nə qədər kredit götürə bilərəm?",
        "Keşbek olan kartlar hansılardır?",
        "Qızıl kredit kartı nədir?",
        "Debet kartların qiymətləri nə qədərdir?",
        "Dostlar klubu kartları kimə verilir?",
        "Kartlarda təmassız ödəniş var?",
        "Kredit kartının müddəti neçə aydır?"
    ]

    for idx, example in enumerate(examples, 1):
        print(f"  {idx}. {example}")

    print()


def main():
    """Main chatbot loop"""
    print_banner()

    # Initialize RAG system
    try:
        print("⏳ Sistem yüklənir...")
        rag = BankCardRAG(data_file="data/rag_chunks.jsonl")

        # Check if data is indexed
        count = rag.collection.count()
        if count == 0:
            print("📥 Məlumatlar indekslənir (ilk dəfə bir neçə saniyə çəkə bilər)...")
            rag.load_and_index_data()
        else:
            print(f"✅ {count} məlumat parçası artıq indekslənilib")

        print("\n✅ Sistem hazırdır! Sualınızı yazın.\n")

    except Exception as e:
        print(f"\n❌ Xəta baş verdi: {str(e)}")
        print("\nZəhmət olmasa .env faylında LLM_API_KEY açarının olduğundan əmin olun.")
        sys.exit(1)

    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = input("👤 Siz: ").strip()

            if not user_input:
                continue

            # Check for exit commands
            if user_input.lower() in ['çıxış', 'exit', 'quit', 'q']:
                print("\n👋 Sağ olun! Yaxşı günlər.\n")
                break

            # Check for help commands
            if user_input.lower() in ['yardım', 'help', 'kömək']:
                print_help()
                continue

            # Process query
            print()  # Empty line for better formatting
            result = rag.query(user_input, n_results=3)

            # Print answer
            print(f"\n🤖 Asistent:\n{result['answer']}\n")

            # Print sources
            if result['sources']:
                print("📎 Mənbələr:")
                seen_sources = set()
                for source in result['sources']:
                    key = f"{source['card_name']} ({source['card_type']})"
                    if key not in seen_sources:
                        print(f"  • {key}")
                        seen_sources.add(key)
                print()

            print("-" * 60 + "\n")

        except KeyboardInterrupt:
            print("\n\n👋 Sağ olun! Yaxşı günlər.\n")
            break

        except Exception as e:
            print(f"\n❌ Xəta: {str(e)}\n")
            continue


if __name__ == "__main__":
    main()
