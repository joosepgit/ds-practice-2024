db.getSiblingDB('admin').auth(
    process.env.MONGO_INITDB_ROOT_USERNAME,
    process.env.MONGO_INITDB_ROOT_PASSWORD
);

db.createUser({
    user: process.env.MONGO_USER,
    pwd: process.env.MONGO_PASSWORD,
    roles: ["readWrite"],
});

db.createCollection("books");

db.books.insertOne({
    title: "Learning Python",
    author: "John Smith",
    description: "An in-depth guide to Python programming.",
    price: 3.00,
    stock: 7
});

db.books.insertOne({
    title: "JavaScript - The Good Parts",
    author: "Jane Doe",
    description: "Unearthing the excellence in JavaScript.",
    price: 3.00,
    stock: 15
});

db.books.insertOne({
    title: "Domain-Driven Design: Tackling Complexity in the Heart of Software",
    author: "Eric Evans",
    description: `The book is a little more technical and challenging than the others,
                  but if you get familiar with these concepts, you’ll be very well off
                  in understanding how today’s largest companies keep their code bases
                  manageable and scalable.`,
    price: 3.00,
    stock: 15
});

db.books.insertOne({
    title: "Design Patterns: Elements of Reusable Object-Oriented Software",
    author: "Erich Gamma, Richard Helm, Ralph Johnson, & John Vlissides",
    description: "Useminal book on Design Patterns.",
    price: 3.00,
    stock: 15
});
