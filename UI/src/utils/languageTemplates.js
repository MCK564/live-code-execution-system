export const LANGUAGE_OPTIONS = [
  { label: "Python", value: "python" },
  { label: "Java", value: "java" },
  { label: "C++", value: "cpp" },
];

export const LANGUAGE_TEMPLATES = {
  python: "print('Hello World')",
  java:
    "public class Main {\n  public static void main(String[] args) {\n    System.out.println(\"Hello World\");\n  }\n}",
  cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n  cout << "Hello World";\n  return 0;\n}',
};
